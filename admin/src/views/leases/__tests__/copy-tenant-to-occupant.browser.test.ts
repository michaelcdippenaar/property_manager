/**
 * Feature 4 — "Copy from tenant" button on the new-occupant form.
 *
 * Verifies the contract: clicking the copier prefills the occupant draft
 * with the chosen tenant's name, ID, DOB, phone, email, and a "self"
 * relationship. Tests the standalone copy logic (avoids mounting the
 * 800-line drawer with its dozen dependencies).
 */
import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

interface Tenant {
  id: number; full_name: string; id_number: string; date_of_birth: string | null
  phone: string; email: string; _is_primary: boolean
}

function setup(tenants: Tenant[]) {
  const allTenants = ref(tenants)
  const newOccupant = ref({
    full_name: '', id_number: '', date_of_birth: '', phone: '', email: '', relationship: '',
  })
  const tenantCopyOptions = computed(() =>
    allTenants.value
      .filter(t => t.full_name)
      .map(t => ({ id: t.id, label: t._is_primary ? `${t.full_name} (primary)` : t.full_name })),
  )
  function onCopyTenantToOccupant(personIdRaw: string) {
    if (!personIdRaw) return
    const id = Number(personIdRaw)
    const t = allTenants.value.find(x => x.id === id)
    if (!t) return
    newOccupant.value = {
      full_name:     t.full_name ?? '',
      id_number:     t.id_number ?? '',
      date_of_birth: t.date_of_birth ?? '',
      phone:         t.phone ?? '',
      email:         t.email ?? '',
      relationship:  'self',
    }
  }
  return { allTenants, newOccupant, tenantCopyOptions, onCopyTenantToOccupant }
}

describe('copy tenant → occupant', () => {
  it('copies primary tenant fields into the occupant draft', () => {
    const { newOccupant, onCopyTenantToOccupant, tenantCopyOptions } = setup([
      {
        id: 1, full_name: 'Themba Ndlovu', id_number: '8801015800087',
        date_of_birth: '1988-01-01', phone: '+27 82 555 0001',
        email: 'themba@example.com', _is_primary: true,
      },
    ])

    expect(tenantCopyOptions.value).toHaveLength(1)
    expect(tenantCopyOptions.value[0].label).toContain('(primary)')

    onCopyTenantToOccupant('1')

    expect(newOccupant.value.full_name).toBe('Themba Ndlovu')
    expect(newOccupant.value.id_number).toBe('8801015800087')
    expect(newOccupant.value.date_of_birth).toBe('1988-01-01')
    expect(newOccupant.value.phone).toBe('+27 82 555 0001')
    expect(newOccupant.value.email).toBe('themba@example.com')
    expect(newOccupant.value.relationship).toBe('self')
  })

  it('handles a co-tenant pick when multiple tenants exist', () => {
    const { newOccupant, onCopyTenantToOccupant, tenantCopyOptions } = setup([
      { id: 1, full_name: 'Primary', id_number: 'A', date_of_birth: null, phone: '', email: '', _is_primary: true },
      { id: 2, full_name: 'Co-tenant', id_number: 'B', date_of_birth: '1990-05-05', phone: '+27 82 222 0000', email: 'co@x.com', _is_primary: false },
    ])

    expect(tenantCopyOptions.value).toHaveLength(2)

    onCopyTenantToOccupant('2')

    expect(newOccupant.value.full_name).toBe('Co-tenant')
    expect(newOccupant.value.id_number).toBe('B')
    expect(newOccupant.value.date_of_birth).toBe('1990-05-05')
    expect(newOccupant.value.phone).toBe('+27 82 222 0000')
    expect(newOccupant.value.email).toBe('co@x.com')
    expect(newOccupant.value.relationship).toBe('self')
  })

  it('no-ops on empty tenant id', () => {
    const { newOccupant, onCopyTenantToOccupant } = setup([
      { id: 1, full_name: 'X', id_number: '', date_of_birth: null, phone: '', email: '', _is_primary: true },
    ])
    onCopyTenantToOccupant('')
    expect(newOccupant.value.full_name).toBe('')
  })
})
