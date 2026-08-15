import { z } from 'zod'

// Material record schemas
export const materialRecordSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  material_type: z.string().min(1, 'Material type is required'),
  core_size_nm: z.number().optional(),
  zeta_potential_mv: z.number().optional(),
  zeta_potential_flagged: z.number().int().min(0).max(1).optional(),
  surface_area_m2g: z.number().min(0).optional(),
  coating: z.string().optional(),
  source_type: z.enum(['literature_mined', 'user_contribution', 'api_sync']),
  doi: z.string().optional(),
  extraction_confidence: z.number().min(0).max(1).optional(),
})

export const materialRecordUpdateSchema = materialRecordSchema.partial()

export type MaterialRecordInput = z.infer<typeof materialRecordSchema>
export type MaterialRecordUpdate = z.infer<typeof materialRecordUpdateSchema>

// Toxicity record schemas
export const toxicityRecordSchema = z.object({
  material_id: z.string().uuid('Invalid material ID'),
  ic50: z.number().positive('IC50 must be positive').optional(),
  ec50: z.number().positive('EC50 must be positive').optional(),
  pec50: z.number().optional(),
  cell_line: z.string().optional(),
  exposure_time_h: z.number().positive('Exposure time must be positive').optional(),
})

export const toxicityRecordUpdateSchema = toxicityRecordSchema.partial()

export type ToxicityRecordInput = z.infer<typeof toxicityRecordSchema>
export type ToxicityRecordUpdate = z.infer<typeof toxicityRecordUpdateSchema>

// Sensor performance record schemas
export const sensorPerformanceRecordSchema = z.object({
  nanomaterial: z.string().min(1, 'Nanomaterial is required'),
  analyte: z.string().min(1, 'Analyte is required'),
  lod_mol_per_l: z.number().positive('LOD must be positive').optional(),
  sensitivity_value: z.number().optional(),
  sensitivity_unit: z.string().optional(),
  linear_range_low: z.number().optional(),
  linear_range_high: z.number().optional(),
  response_time_s: z.number().positive('Response time must be positive').optional(),
  source_type: z.enum(['literature_mined', 'user_contribution', 'api_sync']),
  doi: z.string().optional(),
  extraction_confidence: z.number().min(0).max(1).optional(),
})

export const sensorPerformanceRecordUpdateSchema = sensorPerformanceRecordSchema.partial()

export type SensorPerformanceRecordInput = z.infer<typeof sensorPerformanceRecordSchema>
export type SensorPerformanceRecordUpdate = z.infer<typeof sensorPerformanceRecordUpdateSchema>

// Review schemas
export const recordReviewSchema = z.object({
  record_type: z.enum(['material_record', 'toxicity_record', 'sensor_performance_record']),
  record_id: z.string().uuid('Invalid record ID'),
  status: z.enum(['pending', 'approved', 'rejected']),
  notes: z.string().optional(),
})

export const recordReviewUpdateSchema = z.object({
  status: z.enum(['approved', 'rejected']),
  notes: z.string().optional(),
})

export type RecordReviewInput = z.infer<typeof recordReviewSchema>
export type RecordReviewUpdate = z.infer<typeof recordReviewUpdateSchema>
