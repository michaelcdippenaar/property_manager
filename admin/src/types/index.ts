/**
 * Type barrel — re-exports all entity types so consumers can:
 *
 *   import type { Landlord, Property, Lease } from '@/types'
 *
 * Each file mirrors a Django serializer in `backend/apps/.../serializers.py`.
 */
export * from './landlord'
export * from './property'
export * from './lease'
export * from './ownership'
export * from './person'
export * from './viewing'
export * from './mandate'
