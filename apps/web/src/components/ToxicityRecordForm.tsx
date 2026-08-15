import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toxicityRecordSchema, type ToxicityRecordInput } from '../lib/validation'
import api from '../lib/api'

interface ToxicityRecordFormProps {
  onSuccess?: () => void
  initialData?: Partial<ToxicityRecordInput>
}

function ToxicityRecordForm({ onSuccess, initialData }: ToxicityRecordFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError
  } = useForm<ToxicityRecordInput>({
    resolver: zodResolver(toxicityRecordSchema),
    defaultValues: initialData
  })

  const onSubmit = async (data: ToxicityRecordInput) => {
    try {
      await api.post('/records/toxicity', data)
      if (onSuccess) onSuccess()
    } catch (error: any) {
      setError('root', {
        type: 'manual',
        message: error.response?.data?.detail || 'Failed to create record'
      })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Material ID *</label>
        <input
          {...register('material_id')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.material_id && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.material_id.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>IC50</label>
        <input
          type="number"
          step="0.01"
          {...register('ic50', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.ic50 && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.ic50.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>EC50</label>
        <input
          type="number"
          step="0.01"
          {...register('ec50', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.ec50 && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.ec50.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>pEC50</label>
        <input
          type="number"
          step="0.01"
          {...register('pec50', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.pec50 && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.pec50.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Cell Line</label>
        <input
          {...register('cell_line')}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.cell_line && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.cell_line.message}</span>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.25rem' }}>Exposure Time (hours)</label>
        <input
          type="number"
          step="0.1"
          {...register('exposure_time_h', { valueAsNumber: true })}
          style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc' }}
        />
        {errors.exposure_time_h && <span style={{ color: 'red', fontSize: '0.875rem' }}>{errors.exposure_time_h.message}</span>}
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

export default ToxicityRecordForm