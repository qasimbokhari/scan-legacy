import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { sensorPerformanceRecordSchema, type SensorPerformanceRecordInput } from '../lib/validation'
import api from '../lib/api'

interface SensorPerformanceRecordFormProps {
  onSuccess?: () => void
  initialData?: Partial<SensorPerformanceRecordInput>
}

function SensorPerformanceRecordForm({ onSuccess, initialData }: SensorPerformanceRecordFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError
  } = useForm<SensorPerformanceRecordInput>({
    resolver: zodResolver(sensorPerformanceRecordSchema),
    defaultValues: initialData || {
      source_type: 'user_contribution'
    }
  })

  const onSubmit = async (data: SensorPerformanceRecordInput) => {
    try {
      await api.post('/records/sensor-performance', data)
      if (onSuccess) onSuccess()
    } catch (error: any) {
      if (error.response?.status === 409) {
        setError('root', {
          type: 'manual',
          message: error.response.data.detail || 'Duplicate record detected'
        })
      } else {
        setError('root', {
          type: 'manual',
          message: error.response?.data?.detail || 'Failed to create record'
        })
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Nanomaterial *</label>
        <input
          {...register('nanomaterial')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.nanomaterial && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.nanomaterial.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Analyte *</label>
        <input
          {...register('analyte')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.analyte && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.analyte.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>LOD (mol/L)</label>
        <input
          type="number"
          step="1e-10"
          {...register('lod_mol_per_l', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.lod_mol_per_l && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.lod_mol_per_l.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Sensitivity Value</label>
        <input
          type="number"
          step="0.01"
          {...register('sensitivity_value', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.sensitivity_value && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.sensitivity_value.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Sensitivity Unit</label>
        <input
          {...register('sensitivity_unit')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.sensitivity_unit && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.sensitivity_unit.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Linear Range Low</label>
        <input
          type="number"
          step="0.01"
          {...register('linear_range_low', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.linear_range_low && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.linear_range_low.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Linear Range High</label>
        <input
          type="number"
          step="0.01"
          {...register('linear_range_high', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.linear_range_high && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.linear_range_high.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Response Time (seconds)</label>
        <input
          type="number"
          step="0.1"
          {...register('response_time_s', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.response_time_s && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.response_time_s.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Source Type *</label>
        <select
          {...register('source_type')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        >
          <option value="literature_mined">Literature Mined</option>
          <option value="user_contribution">User Contribution</option>
          <option value="api_sync">API Sync</option>
        </select>
        {errors.source_type && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.source_type.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>DOI</label>
        <input
          {...register('doi')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.doi && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.doi.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Extraction Confidence (0-1)</label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="1"
          {...register('extraction_confidence', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.extraction_confidence && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.extraction_confidence.message}</span>}
      </div>

      {errors.root && <div style={{ color: 'red', padding: '0.5rem', backgroundColor: '#fee' }}>{errors.root.message}</div>}

      <button
        type="submit"
        disabled={isSubmitting}
        style={{
          padding: '0.5rem 1rem',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          cursor: isSubmitting ? 'not-allowed' : 'pointer',
          opacity: isSubmitting ? 0.6 : 1
        }}
      >
        {isSubmitting ? 'Submitting...' : 'Submit Record'}
      </button>
    </form>
  )
}

export default SensorPerformanceRecordForm