import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { materialRecordSchema, type MaterialRecordInput } from '../lib/validation'
import api from '../lib/api'

interface MaterialRecordFormProps {
  onSuccess?: () => void
  initialData?: Partial<MaterialRecordInput>
}

function MaterialRecordForm({ onSuccess, initialData }: MaterialRecordFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError
  } = useForm<MaterialRecordInput>({
    resolver: zodResolver(materialRecordSchema),
    defaultValues: initialData || {
      source_type: 'user_contribution'
    }
  })

  const onSubmit = async (data: MaterialRecordInput) => {
    try {
      await api.post('/records/materials', data)
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
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Name *</label>
        <input
          {...register('name')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.name && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.name.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Material Type *</label>
        <input
          {...register('material_type')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.material_type && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.material_type.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Core Size (nm)</label>
        <input
          type="number"
          step="0.1"
          {...register('core_size_nm', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.core_size_nm && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.core_size_nm.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Zeta Potential (mV)</label>
        <input
          type="number"
          step="0.1"
          {...register('zeta_potential_mv', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.zeta_potential_mv && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.zeta_potential_mv.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Surface Area (m²/g)</label>
        <input
          type="number"
          step="0.1"
          {...register('surface_area_m2g', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.surface_area_m2g && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.surface_area_m2g.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Coating</label>
        <input
          {...register('coating')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.coating && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.coating.message}</span>}
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

export default MaterialRecordForm