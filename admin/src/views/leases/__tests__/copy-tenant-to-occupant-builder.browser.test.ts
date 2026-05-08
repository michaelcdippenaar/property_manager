/**
 * Feature 4 (LeaseBuilderView) — "Same as tenant" copier on each occupant row.
 *
 * Verifies the contract: clicking the copier prefills the targeted occupant
 * with the chosen tenant's name, ID, DOB, phone (+ country code), email,
 * country. `relationship_to_tenant` is NOT overwritten (occupant-specific).
 *
 * Tests the standalone copy logic (mirrors the implementation in
 * LeaseBuilderView.vue's LeaseFormFields component) — avoids mounting the
 * 1500-line builder with its many dependencies.
 */
import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

interface Person {
  full_name: string
  id_number: string
  date_of_birth?: string | null
  phone: string
  phone_country_code?: string
  email: string
  country?: string
}
interface Occupant extends Person {
  relationship_to_tenant: string
}
interface Form {
  primary_tenant: Person
  co_tenants: Person[]
  occupants: Occupant[]
}

function setup(form: Form) {
  const formRef = ref<Form>(form)

  const tenantCopyOptions = computed(() => {
    const f = formRef.value
    const opts: { label: string; source: 'primary' | number }[] = []
    const pt = f?.primary_tenant
    if (pt && (pt.full_name || pt.id_number)) {
      opts.push({ label: `Primary tenant${pt.full_name ? `: ${pt.full_name}` : ''}`, source: 'primary' })
    }
    ;(f?.co_tenants ?? []).forEach((ct, i) => {
      if (ct && (ct.full_name || ct.id_number)) {
        opts.push({ label: `Co-tenant ${i + 1}${ct.full_name ? `: ${ct.full_name}` : ''}`, source: i })
      }
    })
    return opts
  })

  function onCopyTenantToOccupant(occupantIndex: number, source: 'primary' | number | string) {
    if (source === '' || source === undefined || source === null) return
    const f = formRef.value
    const src = source === 'primary' ? f.primary_tenant : f.co_tenants?.[Number(source)]
    if (!src) return
    const occupants = [...(f.occupants ?? [])]
    const current = occupants[occupantIndex] ?? ({} as Occupant)
    occupants[occupantIndex] = {
      ...current,
      full_name:          src.full_name ?? '',
      id_number:          src.id_number ?? '',
      date_of_birth:      src.date_of_birth ?? '',
      phone:              src.phone ?? '',
      phone_country_code: src.phone_country_code ?? '+27',
      email:              src.email ?? '',
      country:            src.country ?? 'ZA',
    }
    formRef.value = { ...f, occupants }
  }

  return { formRef, tenantCopyOptions, onCopyTenantToOccupant }
}

const blankOccupant = (): Occupant => ({
  full_name: '', id_number: '', phone: '', email: '', relationship_to_tenant: 'self',
})

describe('LeaseBuilder: copy tenant -> occupant', () => {
  it('exposes only tenants with content as options', () => {
    const { tenantCopyOptions } = setup({
      primary_tenant: { full_name: 'Themba Ndlovu', id_number: '8801015800087', phone: '', email: '' },
      co_tenants: [
        { full_name: '', id_number: '', phone: '', email: '' }, // blank — filtered
        { full_name: 'Sipho', id_number: '', phone: '', email: '' },
      ],
      occupants: [blankOccupant()],
    })
    expect(tenantCopyOptions.value).toHaveLength(2)
    expect(tenantCopyOptions.value[0]).toMatchObject({ source: 'primary' })
    expect(tenantCopyOptions.value[0].label).toContain('Primary tenant')
    expect(tenantCopyOptions.value[1]).toMatchObject({ source: 1 })
    expect(tenantCopyOptions.value[1].label).toContain('Co-tenant 2')
  })

  it('copies primary tenant fields onto the targeted occupant only', () => {
    const { formRef, onCopyTenantToOccupant } = setup({
      primary_tenant: {
        full_name: 'Themba Ndlovu', id_number: '8801015800087',
        date_of_birth: '1988-01-01', phone: '82 555 0001', phone_country_code: '+27',
        email: 'themba@example.com', country: 'ZA',
      },
      co_tenants: [],
      occupants: [
        { ...blankOccupant(), relationship_to_tenant: 'spouse' },
        { ...blankOccupant(), relationship_to_tenant: 'child' },
      ],
    })

    onCopyTenantToOccupant(0, 'primary')

    const o0 = formRef.value.occupants[0]
    expect(o0.full_name).toBe('Themba Ndlovu')
    expect(o0.id_number).toBe('8801015800087')
    expect(o0.date_of_birth).toBe('1988-01-01')
    expect(o0.phone).toBe('82 555 0001')
    expect(o0.phone_country_code).toBe('+27')
    expect(o0.email).toBe('themba@example.com')
    expect(o0.country).toBe('ZA')
    // relationship_to_tenant must NOT be overwritten
    expect(o0.relationship_to_tenant).toBe('spouse')
    // Sibling occupant untouched
    expect(formRef.value.occupants[1].full_name).toBe('')
    expect(formRef.value.occupants[1].relationship_to_tenant).toBe('child')
  })

  it('copies a co-tenant by index', () => {
    const { formRef, onCopyTenantToOccupant } = setup({
      primary_tenant: { full_name: 'Primary', id_number: 'A', phone: '', email: '' },
      co_tenants: [
        { full_name: 'CoTenantOne', id_number: 'B', date_of_birth: '1990-05-05',
          phone: '82 222 0000', phone_country_code: '+27', email: 'co@x.com', country: 'ZA' },
      ],
      occupants: [blankOccupant()],
    })

    onCopyTenantToOccupant(0, 0)

    const o = formRef.value.occupants[0]
    expect(o.full_name).toBe('CoTenantOne')
    expect(o.id_number).toBe('B')
    expect(o.date_of_birth).toBe('1990-05-05')
    expect(o.phone).toBe('82 222 0000')
    expect(o.email).toBe('co@x.com')
    expect(o.relationship_to_tenant).toBe('self')
  })

  it('no-ops on empty source', () => {
    const { formRef, onCopyTenantToOccupant } = setup({
      primary_tenant: { full_name: 'Primary', id_number: 'A', phone: '', email: '' },
      co_tenants: [],
      occupants: [blankOccupant()],
    })
    onCopyTenantToOccupant(0, '')
    expect(formRef.value.occupants[0].full_name).toBe('')
  })
})
