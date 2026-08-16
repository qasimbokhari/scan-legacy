"""
Analyzer API endpoints for CV/LSV and EIS data analysis.

Provides:
- POST /api/v1/analyzer/cv-lsv - Upload and analyze CV/LSV data
- POST /api/v1/analyzer/eis - Upload and analyze EIS data
- GET /api/v1/analyzer/{id}/results - Retrieve analysis results
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
import numpy as np
from typing import Optional, Union

from app.db.session import get_db
from app.db.models import AnalyzerResult, User
from app.schemas.analyzer import AnalyzerResultOut, AnalyzerErrorResponse
from app.schemas.prediction import PredictionEnvelope
from app.auth.dependencies import get_current_user
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from app.ml.analyzer import (
        parse_cv_lsv_file,
        parse_eis_file,
        detect_peaks,
        calculate_randles_sevcik_diffusion,
        calculate_nicholson_k0,
        calculate_lod_loq,
        fit_eis_circuit,
        generate_nyquist_bode_data
    )
except ImportError:
    from ml.analyzer import (
        parse_cv_lsv_file,
        parse_eis_file,
        detect_peaks,
        calculate_randles_sevcik_diffusion,
        calculate_nicholson_k0,
        calculate_lod_loq,
        fit_eis_circuit,
        generate_nyquist_bode_data
    )

router = APIRouter(prefix="/api/v1/analyzer", tags=["analyzer"])


@router.post("/cv-lsv", response_model=Union[AnalyzerResultOut, AnalyzerErrorResponse])
async def analyze_cv_lsv(
    file: UploadFile = File(...),
    scan_rate_v_s: Optional[float] = None,
    electrode_area_cm2: Optional[float] = None,
    concentration_mol_cm3: Optional[float] = None,
    n_electrons: Optional[int] = 1,
    temperature_k: Optional[float] = 298.15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and analyze CV/LSV data.
    
    Accepts .csv, .txt, .xlsx files with potential and current columns.
    Auto-detects column names and order.
    
    Returns extracted parameters with uncertainty envelopes.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Parse file
        parsed_data = parse_cv_lsv_file(file_content, file.filename)
        
        # Convert to numpy arrays for analysis
        potential = np.array(parsed_data['potential'])
        current = np.array(parsed_data['current'])
        
        # Perform peak detection
        peak_results = detect_peaks(potential, current)
        
        # Initialize processed results
        processed_results = {
            'peaks': peak_results,
            'metadata': parsed_data
        }
        
        # Calculate LOD/LOQ
        try:
            lod_loq_results = calculate_lod_loq(current, potential)
            processed_results['lod_loq'] = {
                'lod': lod_loq_results['lod'].model_dump(),
                'loq': lod_loq_results['loq'].model_dump(),
                'baseline_stats': {
                    'mean': lod_loq_results['baseline_mean'],
                    'std': lod_loq_results['baseline_std'],
                    'n_points': lod_loq_results['n_baseline_points']
                }
            }
        except Exception as e:
            processed_results['lod_loq'] = {
                'error': f"LOD/LOQ calculation failed: {str(e)}"
            }
        
        # Calculate Randles-Sevcik diffusion coefficient if parameters provided
        if (scan_rate_v_s and electrode_area_cm2 and 
            concentration_mol_cm3 and peak_results['anodic_peak']):
            
            try:
                # Use anodic peak current
                peak_current = peak_results['anodic_peak']['current_a']
                
                # Single-point estimate (flag will be added in the function)
                diffusion_result = calculate_randles_sevcik_diffusion(
                    peak_currents=[peak_current],
                    scan_rates=[scan_rate_v_s],
                    electrode_area_cm2=electrode_area_cm2,
                    concentration_mol_cm3=concentration_mol_cm3,
                    n_electrons=n_electrons
                )
                
                processed_results['diffusion_coefficient'] = diffusion_result.model_dump()
            except Exception as e:
                processed_results['diffusion_coefficient'] = {
                    'error': f"Diffusion coefficient calculation failed: {str(e)}"
                }
        
        # Calculate Nicholson k0 if peak separation available and D calculated
        if (peak_results['peak_separation_mv'] and 
            'diffusion_coefficient' in processed_results and
            isinstance(processed_results['diffusion_coefficient'], dict) and
            'value' in processed_results['diffusion_coefficient']):
            
            try:
                D = processed_results['diffusion_coefficient']['value']
                
                nicholson_result = calculate_nicholson_k0(
                    peak_separation_mv=peak_results['peak_separation_mv'],
                    scan_rate_V_s=scan_rate_v_s if scan_rate_v_s else 0.1,  # Default if not provided
                    diffusion_coefficient_cm2_s=D,
                    n_electrons=n_electrons,
                    temperature_K=temperature_k
                )
                
                processed_results['electron_transfer_rate'] = nicholson_result.model_dump()
            except Exception as e:
                processed_results['electron_transfer_rate'] = {
                    'error': f"Nicholson k0 calculation failed: {str(e)}"
                }
        
        # Create database record
        analyzer_result = AnalyzerResult(
            analysis_type="cv-lsv",
            raw_data=parsed_data,
            processed_results=processed_results,
            fit_metadata=None,  # CV/LSV doesn't have circuit fit metadata
            uploaded_by=current_user.id,
            scan_rate_v_s=scan_rate_v_s,
            electrode_area_cm2=electrode_area_cm2,
            concentration_mol_cm3=concentration_mol_cm3,
            n_electrons=n_electrons,
            temperature_k=temperature_k
        )
        
        db.add(analyzer_result)
        db.commit()
        db.refresh(analyzer_result)
        
        return analyzer_result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions from file parser
        if e.status_code == 200:
            # Convert to structured error response
            error_detail = e.detail
            if isinstance(error_detail, dict):
                return AnalyzerErrorResponse(**error_detail)
        # For other HTTP exceptions, convert to structured error
        return AnalyzerErrorResponse(
            success=False,
            error=str(e.detail),
            error_type="parse_error"
        )
        
    except Exception as e:
        # Handle unexpected errors
        return AnalyzerErrorResponse(
            success=False,
            error=f"Analysis failed: {str(e)}",
            error_type="fit_error"
        )


@router.post("/eis", response_model=Union[AnalyzerResultOut, AnalyzerErrorResponse])
async def analyze_eis(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and analyze EIS data.
    
    Accepts .csv, .txt files with frequency, Z_real, and Z_imag columns.
    Auto-detects column names and order.
    
    Returns fitted Randles circuit parameters with uncertainty envelopes,
    plus Nyquist and Bode plot data.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Parse file
        parsed_data = parse_eis_file(file_content, file.filename)
        
        # Convert to numpy arrays for analysis
        frequency = np.array(parsed_data['frequency'])
        z_real = np.array(parsed_data['Z_real'])
        z_imag = np.array(parsed_data['Z_imag'])
        
        # Fit Randles circuit
        circuit_fit_results = fit_eis_circuit(frequency, z_real, z_imag)
        
        # Extract fitted parameters for plotting data generation
        fitted_params = {
            'Rs': circuit_fit_results['Rs'].value,
            'Rct': circuit_fit_results['Rct'].value,
            'Cdl': circuit_fit_results['Cdl'].value,
            'warburg': circuit_fit_results['warburg_coefficient'].value
        }
        
        # Generate Nyquist and Bode data
        plot_data = generate_nyquist_bode_data(
            frequency, z_real, z_imag, fitted_params
        )
        
        # Prepare processed results
        processed_results = {
            'circuit_parameters': {
                'Rs': circuit_fit_results['Rs'].model_dump(),
                'Rct': circuit_fit_results['Rct'].model_dump(),
                'Cdl': circuit_fit_results['Cdl'].model_dump(),
                'warburg_coefficient': circuit_fit_results['warburg_coefficient'].model_dump()
            },
            'fit_quality': circuit_fit_results['fit_quality'],
            'plot_data': plot_data,
            'metadata': parsed_data
        }
        
        # Create database record
        analyzer_result = AnalyzerResult(
            analysis_type="eis",
            raw_data=parsed_data,
            processed_results=processed_results,
            fit_metadata=circuit_fit_results['fit_quality'],
            uploaded_by=current_user.id
        )
        
        db.add(analyzer_result)
        db.commit()
        db.refresh(analyzer_result)
        
        return analyzer_result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions from file parser
        if e.status_code == 200:
            # Convert to structured error response
            error_detail = e.detail
            if isinstance(error_detail, dict):
                return AnalyzerErrorResponse(**error_detail)
        # For other HTTP exceptions, convert to structured error
        return AnalyzerErrorResponse(
            success=False,
            error=str(e.detail),
            error_type="parse_error"
        )
        
    except Exception as e:
        # Handle unexpected errors
        return AnalyzerErrorResponse(
            success=False,
            error=f"EIS analysis failed: {str(e)}",
            error_type="fit_error"
        )


@router.get("/{analysis_id}/results", response_model=AnalyzerResultOut)
def get_analysis_results(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve analysis results by ID.
    
    Results are scoped to the user's team/workspace.
    """
    # Query the analysis result
    result = db.query(AnalyzerResult).filter(
        AnalyzerResult.id == analysis_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found"
        )
    
    # Check access control - user can only see their own results
    # (Team/workspace access control can be extended here)
    if result.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you can only view your own analysis results"
        )
    
    return result