<template>
  <div class="space-y-5">

    <!-- ── Page header ── -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          aria-label="Back"
          @click="$router.back()"
        >
          <ArrowLeft :size="18" />
        </button>
        <div>
          <h1 class="text-xl font-bold text-gray-900">{{ property?.name ?? '…' }}</h1>
          <div v-if="property?.units?.length" class="flex items-center gap-1.5 mt-0.5">
            <select
              :value="activeUnit"
              @change="switchUnit(Number(($event.target as HTMLSelectElement).value))"
              class="text-xs text-gray-500 bg-transparent border-none p-0 pr-4 cursor-pointer hover:text-navy focus:outline-none focus:text-navy appearance-none"
              style="background-image: url('data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2712%27 height=%2712%27 fill=%27none%27 stroke=%27%239ca3af%27 stroke-width=%272%27%3E%3Cpath d=%27M3 5l3 3 3-3%27/%3E%3C/svg%3E'); background-repeat: no-repeat; background-position: right center; background-size: 12px;"
            >
              <option v-for="u in property.units" :key="u.id" :value="u.id">
                Unit {{ u.unit_number }}
              </option>
            </select>
            <span class="inline-flex items-center gap-1 text-xs text-gray-500"
              :aria-label="`Unit status: ${activeUnitData?.status ?? 'unknown'}`"
            >
              <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                :class="{
                  'bg-success-500': activeUnitData?.status === 'occupied',
                  'bg-info-400':    activeUnitData?.status === 'available',
                  'bg-warning-400': activeUnitData?.status === 'maintenance',
                  'bg-gray-300':    !activeUnitData?.status,
                }"
              />
              <span class="capitalize">{{ activeUnitData?.status ?? '—' }}</span>
            </span>
          </div>
          <p v-else class="text-xs text-gray-400 mt-0.5">{{ property?.address }}</p>
        </div>
      </div>

      <div class="relative" ref="menuRef">
        <button
          class="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
          @click="menuOpen = !menuOpen"
        >
          <MoreHorizontal :size="16" /> Actions
        </button>
        <Transition
          enter-active-class="transition ease-out duration-100"
          enter-from-class="opacity-0 scale-95 -translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition ease-in duration-75"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 -translate-y-1"
        >
          <div v-if="menuOpen" class="absolute right-0 mt-1.5 w-56 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1 origin-top-right">
            <button class="menu-item" @click="menuOpen = false; goCreateLease()">
              <FileSignature :size="15" class="text-gray-400" /> Create lease
            </button>
            <button class="menu-item" @click="handleAdvertise">
              <Megaphone :size="15" class="text-gray-400" /> Advertise unit
            </button>
            <button class="menu-item" @click="handleGenerateLease">
              <FilePlus2 :size="15" class="text-gray-400" /> Renew lease
            </button>
            <div class="my-1 border-t border-gray-100" />
            <button class="menu-item text-warning-600 hover:bg-warning-50" @click="handleArchive">
              <FolderOpen :size="15" /> Archive property
            </button>
            <button class="menu-item text-danger-500 hover:bg-danger-50" @click="handleVoidLease">
              <Ban :size="15" /> Void lease
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-3 gap-5 animate-pulse">
      <div class="col-span-2 space-y-4">
        <div class="h-12 bg-gray-100 rounded-xl" />
        <div class="h-56 bg-gray-100 rounded-xl" />
        <div class="h-32 bg-gray-100 rounded-xl" />
      </div>
      <div class="space-y-4">
        <div class="h-32 bg-gray-100 rounded-xl" />
        <div class="h-24 bg-gray-100 rounded-xl" />
        <div class="h-24 bg-gray-100 rounded-xl" />
      </div>
    </div>

    <template v-else-if="property">

      <!-- ── Section tabs ── -->
      <div class="-mx-6 px-6 border-b border-gray-200 flex items-center gap-0 mb-5">
        <button
          v-for="tab in sectionTabs"
          :key="tab.key"
          class="px-4 py-2 text-sm font-medium transition-colors relative flex items-center gap-1.5"
          :class="activeSection === tab.key ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
          @click="activeSection = tab.key"
        >
          <component :is="tab.icon" :size="13" />
          {{ tab.label }}
          <span
            v-if="tab.key === 'maintenance' && openMaintenance.length > 0"
            class="ml-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-danger-500 text-white text-[10px] font-bold leading-none"
          >{{ openMaintenance.length }}</span>
          <span v-if="activeSection === tab.key" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
        </button>
      </div>

      <!-- ── Overview (comprehensive property dashboard) ── -->
      <div v-if="activeSection === 'overview'" class="space-y-5">

        <!-- HERO STRIP -->
        <div class="card overflow-hidden">
          <div class="flex items-center gap-5 p-5">
            <!-- Cover photo -->
            <div class="w-20 h-20 rounded-xl bg-gray-100 flex-shrink-0 overflow-hidden flex items-center justify-center">
              <img
                v-if="property.cover_photo"
                :src="property.cover_photo"
                class="w-full h-full object-cover"
                alt="Property cover"
              />
              <Home v-else :size="28" class="text-gray-300" />
            </div>

            <!-- Identity -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="text-base font-semibold text-gray-900">{{ property.name }}</h3>
                <span class="badge-gray capitalize">{{ property.property_type }}</span>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ property.address }}<span v-if="property.city">, {{ property.city }}</span></p>
            </div>

            <!-- 4 stat tiles -->
            <div class="flex items-center gap-3 flex-shrink-0">
              <div class="text-center px-4 py-2.5 rounded-xl bg-gray-50 border border-gray-100">
                <div class="text-lg font-bold text-gray-900">{{ totalUnits }}</div>
                <div class="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">Units</div>
              </div>
              <div class="text-center px-4 py-2.5 rounded-xl bg-gray-50 border border-gray-100">
                <div class="text-lg font-bold text-success-600">{{ occupiedUnits }}</div>
                <div class="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">Occupied</div>
              </div>
              <div class="text-center px-4 py-2.5 rounded-xl bg-gray-50 border border-gray-100">
                <div class="text-lg font-bold text-navy">R{{ totalMonthlyIncome.toLocaleString('en-ZA', { maximumFractionDigits: 0 }) }}</div>
                <div class="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">Monthly income</div>
              </div>
              <div class="text-center px-4 py-2.5 rounded-xl bg-gray-50 border border-gray-100">
                <div class="text-lg font-bold" :class="openMaintenance.length > 0 ? 'text-warning-600' : 'text-gray-400'">{{ openMaintenance.length }}</div>
                <div class="text-[10px] text-gray-400 uppercase tracking-wide mt-0.5">Open jobs</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 2-COL GRID -->
        <div class="grid grid-cols-3 gap-5">

          <!-- LEFT 2/3 -->
          <div class="col-span-2 space-y-4">

            <!-- Active Lease(s) -->
            <div class="card overflow-hidden">
              <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <FileSignature :size="14" class="text-navy" />
                  <span class="text-xs font-semibold uppercase tracking-wide text-navy">
                    {{ currentLeases.length > 1 ? 'Active Leases' : 'Active Lease' }}
                  </span>
                  <span v-if="currentLeases.length > 1" class="text-xs text-gray-400">({{ currentLeases.length }})</span>
                </div>
                <div v-if="loadingLease" class="h-3 w-12 bg-gray-100 rounded animate-pulse" />
                <button v-else-if="!currentLeases.length" class="text-xs text-navy hover:underline" @click.stop="goCreateLease()">Create lease</button>
                <button v-else class="text-xs text-navy hover:underline" @click.stop="activeSection = 'leases'">View all</button>
              </div>

              <div v-if="loadingLease" class="p-5 space-y-3 animate-pulse">
                <div class="h-8 bg-gray-100 rounded" />
                <div class="h-8 bg-gray-100 rounded" />
              </div>

              <div v-else-if="currentLeases.length" class="divide-y divide-gray-50">
                <div
                  v-for="lease in currentLeases"
                  :key="lease.id"
                  class="px-5 py-4 space-y-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  @click="$router.push({ path: '/leases', query: { expand: lease.id } })"
                >
                  <div class="flex items-center gap-2">
                    <span :class="lease.status === 'active' ? 'badge-green' : 'badge-purple'">
                      {{ lease.status === 'active' ? 'Active' : 'Pending' }}
                    </span>
                    <span class="text-sm font-semibold text-gray-900">{{ lease.lease_number || `Lease #${lease.id}` }}</span>
                  </div>
                  <div class="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div class="text-xs text-gray-400 mb-0.5">Tenant</div>
                      <div class="font-medium text-gray-900">{{ lease.primary_tenant_name || lease.primary_tenant?.full_name || '—' }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400 mb-0.5">Period</div>
                      <div class="text-gray-700">{{ fmtDate(lease.start_date) }} → {{ fmtDate(lease.end_date) }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400 mb-0.5">Monthly rent</div>
                      <div class="font-medium text-gray-900">R{{ Number(lease.monthly_rent).toLocaleString('en-ZA') }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="px-5 py-8 text-center">
                <FileSignature :size="28" class="mx-auto text-gray-200 mb-2" />
                <p class="text-xs text-gray-400">No active lease for this unit.</p>
                <button class="btn-ghost btn-sm mt-3" @click.stop="goCreateLease()">Create lease</button>
              </div>
            </div>

            <!-- Open Maintenance (all units) -->
            <div class="card overflow-hidden">
              <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <Wrench :size="14" class="text-navy" />
                  <span class="text-xs font-semibold uppercase tracking-wide text-navy">Open Maintenance</span>
                </div>
                <button
                  v-if="openMaintenance.length"
                  class="text-xs text-navy hover:underline"
                  @click="activeSection = 'maintenance'"
                >View all</button>
              </div>

              <div v-if="loadingMaintenance" class="p-5 space-y-3 animate-pulse">
                <div v-for="i in 3" :key="i" class="h-10 bg-gray-100 rounded" />
              </div>

              <div v-else-if="openMaintenance.length" class="divide-y divide-gray-50">
                <div
                  v-for="req in openMaintenance.slice(0, 5)"
                  :key="req.id"
                  class="px-5 py-3 flex items-center justify-between gap-3"
                >
                  <div class="min-w-0">
                    <div class="text-sm text-gray-800 truncate">{{ req.title }}</div>
                    <div class="text-xs text-gray-400 mt-0.5">{{ req.category }}</div>
                  </div>
                  <span class="flex-shrink-0" :class="{
                    'badge-red':   req.priority === 'urgent',
                    'badge-amber': req.priority === 'high',
                    'badge-gray':  req.priority === 'medium' || req.priority === 'low',
                  }">{{ req.priority }}</span>
                </div>
              </div>

              <div v-else class="px-5 py-8 text-center">
                <CheckCircle :size="28" class="mx-auto text-success-400 mb-2" />
                <p class="text-xs text-gray-400">No open maintenance issues.</p>
              </div>
            </div>

          </div>

          <!-- RIGHT 1/3 -->
          <div class="space-y-4">

            <!-- Owner Summary -->
            <div class="card p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div class="text-xs font-semibold uppercase tracking-wide text-navy">Owner</div>
                <button class="text-xs text-navy hover:underline" @click="activeSection = 'landlord'">View details →</button>
              </div>

              <div v-if="loadingOwner" class="space-y-2 animate-pulse">
                <div class="h-4 bg-gray-100 rounded w-3/4" />
                <div class="h-3 bg-gray-100 rounded w-1/2" />
              </div>

              <template v-else-if="owner">
                <div class="text-sm font-semibold text-gray-900">{{ owner.owner_name }}</div>
                <div class="text-xs text-gray-400 capitalize">{{ owner.owner_type }}</div>
                <div v-if="owner.owner_phone || owner.owner_email" class="space-y-1.5 text-xs">
                  <a v-if="owner.owner_phone" :href="`tel:${owner.owner_phone}`" class="flex items-center gap-1.5 text-gray-600 hover:text-navy">
                    <Phone :size="11" class="text-gray-400 flex-shrink-0" /> {{ owner.owner_phone }}
                  </a>
                  <a v-if="owner.owner_email" :href="`mailto:${owner.owner_email}`" class="flex items-center gap-1.5 text-gray-600 hover:text-navy truncate">
                    <Mail :size="11" class="text-gray-400 flex-shrink-0" /> {{ owner.owner_email }}
                  </a>
                </div>
              </template>

              <div v-else class="text-xs text-gray-400">No owner on record.</div>
            </div>

            <!-- Lease Template -->
            <div class="card p-4 space-y-3">
              <div class="text-xs font-semibold uppercase tracking-wide text-navy">Lease Template</div>
              <div v-if="loadingTemplate" class="h-4 bg-gray-100 rounded animate-pulse" />
              <div v-else-if="linkedTemplate" class="space-y-2">
                <div class="flex items-center gap-2">
                  <div class="w-7 h-7 rounded-lg bg-surface-secondary flex items-center justify-center flex-shrink-0">
                    <FileSignature :size="13" class="text-navy" />
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm font-medium text-gray-900 truncate">{{ linkedTemplate.name }}</div>
                    <div class="text-xs text-gray-400 capitalize">{{ linkedTemplate.template_type?.replace(/_/g, ' ') || 'Lease template' }}</div>
                  </div>
                </div>
                <RouterLink :to="`/leases/templates/${linkedTemplate.id}/edit`" class="text-xs text-navy hover:underline">Open →</RouterLink>
              </div>
              <div v-else class="space-y-1">
                <p class="text-xs text-gray-400">No template linked.</p>
                <RouterLink to="/leases/templates" class="text-xs text-navy hover:underline">Browse →</RouterLink>
              </div>
            </div>

          </div>
        </div>

      </div>

      <!-- ── Leases tab ── -->
      <div v-else-if="activeSection === 'leases'" class="space-y-4 pt-6">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500">All leases for this unit.</p>
          <button class="btn-ghost btn-sm" @click="goCreateLease()">
            <FilePlus2 :size="14" /> New lease
          </button>
        </div>

        <!-- Active / pending leases -->
        <div v-if="loadingLease || loadingPrevLeases" class="card p-5 animate-pulse"><div class="h-20 bg-gray-100 rounded" /></div>
        <template v-else>
          <div
            v-for="lease in currentLeases"
            :key="lease.id"
            class="card p-5 space-y-3 cursor-pointer hover:shadow-md transition-shadow"
            @click="$router.push({ path: '/leases', query: { expand: lease.id } })"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="lease.status === 'active' ? 'badge-green' : 'badge-purple'">
                  {{ lease.status === 'active' ? 'Active' : 'Pending' }}
                </span>
                <span class="text-sm font-semibold text-gray-900">{{ lease.lease_number || `Lease #${lease.id}` }}</span>
              </div>
              <ChevronRight :size="16" class="text-gray-400" />
            </div>
            <div class="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div class="text-xs text-gray-400 mb-0.5">Tenant</div>
                <div class="font-medium text-gray-900">{{ lease.primary_tenant_name || lease.primary_tenant?.full_name || '—' }}</div>
              </div>
              <div>
                <div class="text-xs text-gray-400 mb-0.5">Period</div>
                <div class="text-gray-700">{{ fmtDate(lease.start_date) }} → {{ fmtDate(lease.end_date) }}</div>
              </div>
              <div>
                <div class="text-xs text-gray-400 mb-0.5">Monthly rent</div>
                <div class="font-medium text-gray-900">R{{ Number(lease.monthly_rent).toLocaleString('en-ZA') }}</div>
              </div>
            </div>
          </div>
        </template>

        <!-- Previous leases -->
        <div v-if="previousLeases.length" class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">Previous leases</p>
          <div
            v-for="lease in previousLeases"
            :key="lease.id"
            class="card p-4 flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow"
            @click="$router.push({ path: '/leases', query: { expand: lease.id } })"
          >
            <span :class="{
              'badge-gray': lease.status === 'expired',
              'badge-red':  lease.status === 'cancelled' || lease.status === 'voided',
              'badge-amber': lease.status === 'draft',
            }">{{ lease.status }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-900">{{ lease.lease_number || `Lease #${lease.id}` }}</div>
              <div class="text-xs text-gray-400">{{ fmtDate(lease.start_date) }} → {{ fmtDate(lease.end_date) }}</div>
            </div>
            <div class="text-sm text-gray-600">R{{ Number(lease.monthly_rent).toLocaleString('en-ZA') }}</div>
            <ChevronRight :size="14" class="text-gray-400 flex-shrink-0" />
          </div>
        </div>

        <EmptyState
          v-if="!loadingLease && !loadingPrevLeases && !currentLeases.length && !previousLeases.length"
          title="No leases yet"
          description="Create a lease to get started."
          :icon="FileSignature"
        >
          <button class="btn-primary" @click="goCreateLease()">
            <Plus :size="15" /> Create lease
          </button>
        </EmptyState>
      </div>

      <!-- ── Documentation tab ── -->
      <!-- ── Mandate tab ── -->
      <div v-else-if="activeSection === 'mandate'">
        <MandateTab :property-id="Number(route.params.id)" />
      </div>

      <div v-else-if="activeSection === 'documentation'" class="space-y-4">
        <div>
          <p class="text-sm text-gray-500">Property documents required for purchase, compliance, and management in South Africa.</p>
        </div>

        <!-- Document categories grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div v-for="cat in docCategories" :key="cat.key" class="card">
            <div class="px-4 py-3 border-b border-gray-100">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <component :is="cat.icon" :size="14" class="text-navy" />
                  <span class="text-xs font-semibold text-gray-800">{{ cat.label }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span v-if="docsByCategory[cat.key]?.length" class="text-[10px] font-semibold text-navy bg-surface-secondary px-1.5 py-0.5 rounded-full">{{ docsByCategory[cat.key].length }}</span>
                  <label class="btn-ghost btn-sm cursor-pointer !py-0.5 !px-2 !text-[11px]">
                    <Upload :size="11" /> Upload
                    <input type="file" class="hidden" @change="(e: Event) => uploadDocForCategory(e, cat.types[0])" />
                  </label>
                </div>
              </div>
              <p class="text-[10px] text-gray-400 mt-1">{{ cat.desc }}</p>
            </div>

            <div v-if="docsByCategory[cat.key]?.length" class="divide-y divide-gray-50">
              <div
                v-for="doc in docsByCategory[cat.key]"
                :key="doc.id"
                class="px-4 py-2.5 flex items-center justify-between gap-2 hover:bg-gray-50 transition-colors"
              >
                <a
                  :href="doc.file_url"
                  target="_blank"
                  class="flex items-center gap-2 text-xs text-gray-700 hover:text-navy truncate min-w-0"
                >
                  <FileText :size="13" class="text-gray-400 flex-shrink-0" />
                  <div class="min-w-0">
                    <div class="font-medium truncate">{{ doc.name }}</div>
                    <div class="text-[10px] text-gray-400 mt-0.5">{{ fmtDate(doc.uploaded_at) }}</div>
                  </div>
                </a>
                <span class="badge-gray text-[9px] flex-shrink-0 capitalize">{{ doc.doc_type.replace(/_/g, ' ') }}</span>
              </div>
            </div>

            <div v-else class="px-4 py-2">
              <EmptyState title="No documents" description="Upload documents for this category." :icon="FileText" />
            </div>
          </div>
        </div>

        <!-- House & estate rules -->
        <div class="card p-5 space-y-4">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">House & Estate Rules</div>
          <textarea
            v-model="houseRules"
            class="input h-28 resize-none text-sm"
            placeholder="Parking, noise hours, pets, visitors, refuse collection, braai areas…"
            @blur="saveHouseRules"
          />
          <p v-if="rulesSaved" class="text-[11px] text-success-600 mt-1">Saved</p>
        </div>
      </div>

      <!-- ── Inventory tab ── -->
      <div v-else-if="activeSection === 'inventory'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500">
            <template v-if="activeLease">Inventory for lease {{ activeLease.lease_number || `#${activeLease.id}` }}.</template>
            <template v-else>No active lease — inventory is tied to a lease period.</template>
          </p>
          <div v-if="activeLease" class="flex items-center gap-2">
            <button class="btn-ghost btn-sm" @click="showTemplateModal = true">
              <ClipboardList :size="14" /> From template
            </button>
            <button class="btn-primary btn-sm" @click="openAddItem">
              <Plus :size="14" /> Add item
            </button>
          </div>
        </div>

        <div v-if="!activeLease" class="card p-6">
          <EmptyState title="No active lease" description="Inventory items are tracked per lease period." :icon="ClipboardList" />
        </div>

        <template v-else>
          <!-- Loading -->
          <div v-if="loadingInventory" class="card p-0 overflow-hidden">
            <table class="table-wrap">
              <thead><tr><th scope="col">Item</th><th scope="col">Category</th><th scope="col">Condition</th><th scope="col">Barcode</th><th scope="col" class="text-right">Actions</th></tr></thead>
              <tbody>
                <tr v-for="i in 4" :key="i">
                  <td><div class="h-4 bg-gray-100 rounded animate-pulse w-3/4" /></td>
                  <td><div class="h-4 bg-gray-100 rounded animate-pulse w-1/2" /></td>
                  <td><div class="h-4 bg-gray-100 rounded animate-pulse w-1/3" /></td>
                  <td><div class="h-4 bg-gray-100 rounded animate-pulse w-1/2" /></td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Items table -->
          <div v-else-if="inventoryItems.length" class="card p-0 overflow-hidden">
            <table class="table-wrap">
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th scope="col">Category</th>
                  <th scope="col">Qty</th>
                  <th scope="col">Condition In</th>
                  <th scope="col">Condition Out</th>
                  <th scope="col">Barcode</th>
                  <th scope="col">Photo</th>
                  <th scope="col" class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in inventoryItems" :key="item.id">
                  <td>
                    <div class="font-medium text-gray-900">{{ item.name }}</div>
                    <div v-if="item.notes" class="text-xs text-gray-400 truncate max-w-[200px]">{{ item.notes }}</div>
                  </td>
                  <td><span class="badge-gray capitalize text-[10px]">{{ item.category }}</span></td>
                  <td class="text-gray-700">{{ item.quantity }}</td>
                  <td><span :class="conditionBadge(item.condition_in)">{{ item.condition_in }}</span></td>
                  <td>
                    <span v-if="item.condition_out" :class="conditionBadge(item.condition_out)">{{ item.condition_out }}</span>
                    <span v-else class="text-xs text-gray-300">—</span>
                  </td>
                  <td>
                    <span v-if="item.barcode" class="font-mono text-xs text-gray-600 bg-gray-50 px-1.5 py-0.5 rounded">{{ item.barcode }}</span>
                    <span v-else class="text-xs text-gray-300">—</span>
                  </td>
                  <td>
                    <div class="flex items-center gap-1">
                      <img v-if="item.photo_in" :src="item.photo_in" class="w-8 h-8 rounded object-cover border border-gray-200" alt="Move-in" />
                      <img v-if="item.photo_out" :src="item.photo_out" class="w-8 h-8 rounded object-cover border border-gray-200" alt="Move-out" />
                      <span v-if="!item.photo_in && !item.photo_out" class="text-xs text-gray-300">—</span>
                    </div>
                  </td>
                  <td class="text-right">
                    <div class="flex items-center justify-end gap-1">
                      <button class="btn-ghost btn-xs" aria-label="Edit item" @click="editItem(item)">Edit</button>
                      <button class="btn-ghost btn-xs text-danger-500" aria-label="Delete item" @click="deleteInventoryItem(item)">Delete</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Empty -->
          <div v-else class="card p-6">
            <EmptyState title="No inventory items" description="Add items to track furniture, appliances, and fixtures for this lease." :icon="ClipboardList">
              <button class="btn-primary btn-sm" @click="openAddItem">
                <Plus :size="14" /> Add first item
              </button>
            </EmptyState>
          </div>
        </template>
      </div>

      <!-- ── Maintenance & Tasks tab ── -->
      <div v-else-if="activeSection === 'maintenance'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500">Maintenance requests and tasks for this property.</p>
          <RouterLink to="/maintenance/issues" class="btn-primary btn-sm">
            <Wrench :size="14" /> All requests
          </RouterLink>
        </div>

        <div class="card">
          <div class="px-5 py-3 border-b border-gray-100">
            <span class="text-xs font-semibold uppercase tracking-wide text-navy">Open Requests</span>
          </div>

          <div v-if="loadingMaintenance" class="p-5 space-y-3 animate-pulse">
            <div v-for="i in 3" :key="i" class="h-4 bg-gray-100 rounded" />
          </div>

          <div v-else-if="openMaintenance.length" class="divide-y divide-gray-50">
            <div
              v-for="req in openMaintenance"
              :key="req.id"
              class="px-5 py-3 flex items-center justify-between gap-3 hover:bg-gray-50 transition-colors cursor-pointer"
              @click="router.push('/maintenance/issues')"
            >
              <div class="min-w-0">
                <div class="text-sm font-medium text-gray-800 truncate">{{ req.title }}</div>
                <div class="text-xs text-gray-400 mt-0.5">{{ req.unit ?? '' }}</div>
              </div>
              <span
                class="flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                :class="{
                  'bg-danger-50 text-danger-600':  req.priority === 'urgent' || req.priority === 'high',
                  'bg-warning-50 text-warning-600': req.priority === 'medium',
                  'bg-gray-100 text-gray-500':      req.priority === 'low',
                }"
              >{{ req.priority }}</span>
            </div>
          </div>

          <EmptyState
            v-else
            title="No open requests"
            description="All maintenance requests are resolved."
            :icon="Wrench"
          />
        </div>
      </div>

      <!-- ── Advertising tab ── -->
      <div v-else-if="activeSection === 'advertising'" class="space-y-4">
        <p class="text-sm text-gray-500">Unit listing details, photos, and advertising description.</p>

        <!-- Unit specs grid -->
        <div v-if="activeUnitData" class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy mb-3">Unit Specs</div>
          <div class="grid grid-cols-3 sm:grid-cols-6 gap-4 text-sm">
            <div>
              <div class="text-xs text-gray-400">Bedrooms</div>
              <div class="font-semibold text-gray-900">{{ activeUnitData.bedrooms }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Bathrooms</div>
              <div class="font-semibold text-gray-900">{{ activeUnitData.bathrooms }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Toilets</div>
              <div class="font-semibold text-gray-900">{{ activeUnitData.toilets ?? 1 }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Floor size</div>
              <div class="font-semibold text-gray-900">{{ activeUnitData.floor_size_m2 ? `${activeUnitData.floor_size_m2} m²` : '—' }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Base rent</div>
              <div class="font-semibold text-gray-900">R{{ Number(activeUnitData.rent_amount).toLocaleString('en-ZA', { maximumFractionDigits: 0 }) }}/mo</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Floor</div>
              <div class="font-semibold text-gray-900">{{ activeUnitData.floor ?? 'G' }}</div>
            </div>
          </div>
        </div>

        <!-- Listing description (unit-level if a unit is selected, otherwise property-level) -->
        <div class="card p-5 space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Listing Description</div>
          <textarea
            v-model="adDescription"
            class="input h-32 resize-none text-sm"
            :placeholder="activeUnit ? 'Write a compelling description for this unit listing…' : 'Write a compelling description for this property listing…'"
            @blur="saveAdDescription"
          />
          <p v-if="adSaved" class="text-[11px] text-success-600">Saved</p>
        </div>

        <!-- Photos -->
        <div class="card p-5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy">Photos</div>
            <label class="btn-primary btn-sm cursor-pointer" :class="uploadingPhotos ? 'pointer-events-none opacity-70' : ''">
              <Loader2 v-if="uploadingPhotos" :size="14" class="animate-spin" />
              <ImagePlus v-else :size="14" />
              {{ uploadingPhotos ? 'Uploading…' : 'Upload photos' }}
              <input type="file" multiple accept="image/*" class="hidden" :disabled="uploadingPhotos" @change="uploadPhotos" />
            </label>
          </div>

          <!-- Upload progress bar -->
          <div v-if="uploadingPhotos" class="space-y-1.5">
            <div class="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
              <div
                class="bg-navy h-1.5 rounded-full transition-all duration-300"
                :style="{ width: uploadProgress + '%' }"
              />
            </div>
            <p class="text-xs text-gray-400 text-right">{{ uploadProgress }}%</p>
          </div>

          <div v-if="loadingPhotos" class="grid grid-cols-4 gap-3 animate-pulse">
            <div v-for="i in 4" :key="i" class="aspect-[4/3] bg-gray-100 rounded-lg" />
          </div>

          <div v-else-if="unitPhotos.length" class="grid grid-cols-8 gap-2">
            <div
              v-for="photo in unitPhotos"
              :key="photo.id"
              class="relative aspect-square rounded-lg overflow-hidden bg-gray-100 group"
            >
              <img
                :src="photo.thumbnail_url || photo.photo_url"
                class="w-full h-full object-cover"
                :alt="photo.caption || 'Unit photo'"
              />
              <button
                class="absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                @click="deletePhoto(photo)"
                title="Delete photo"
              >
                <X :size="12" />
              </button>
            </div>
          </div>

          <div v-else class="py-4">
            <EmptyState title="No photos yet" description="Upload photos to showcase this unit in listings." :icon="ImagePlus" />
          </div>
        </div>
      </div>

      <!-- ── Landlord tab ── -->
      <div v-else-if="activeSection === 'landlord'" class="space-y-4">
        <p class="text-sm text-gray-500">Owner and representative information for this property.</p>

        <div v-if="loadingOwner" class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-pulse">
          <div class="card p-5"><div class="h-32 bg-gray-100 rounded" /></div>
          <div class="card p-5"><div class="h-32 bg-gray-100 rounded" /></div>
        </div>

        <template v-else-if="owner">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Owner entity -->
            <div class="card p-5 space-y-3">
              <div class="text-xs font-semibold uppercase tracking-wide text-navy">Owner Entity</div>
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-surface-secondary flex items-center justify-center flex-shrink-0">
                  <Building2 :size="18" class="text-navy" />
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-semibold text-gray-900">{{ owner.owner_name }}</div>
                  <div class="text-xs text-gray-400 capitalize">{{ owner.owner_type }}</div>
                </div>
              </div>

              <div class="space-y-2 text-xs">
                <div v-if="owner.registration_number" class="flex justify-between">
                  <span class="text-gray-400">Registration</span>
                  <span class="text-gray-700 font-medium">{{ owner.registration_number }}</span>
                </div>
                <div v-if="owner.vat_number" class="flex justify-between">
                  <span class="text-gray-400">VAT number</span>
                  <span class="text-gray-700 font-medium">{{ owner.vat_number }}</span>
                </div>
                <div v-if="owner.owner_email" class="flex justify-between">
                  <span class="text-gray-400">Email</span>
                  <a :href="`mailto:${owner.owner_email}`" class="text-navy hover:underline">{{ owner.owner_email }}</a>
                </div>
                <div v-if="owner.owner_phone" class="flex justify-between">
                  <span class="text-gray-400">Phone</span>
                  <a :href="`tel:${owner.owner_phone}`" class="text-gray-700 hover:text-navy">{{ owner.owner_phone }}</a>
                </div>
              </div>

              <div v-if="owner.owner_address?.street" class="border-t border-gray-100 pt-2.5 text-xs text-gray-600">
                <div class="text-gray-400 text-[10px] uppercase tracking-wide mb-1">Address</div>
                <div>{{ owner.owner_address.street }}</div>
                <div v-if="owner.owner_address.city">{{ owner.owner_address.city }}<span v-if="owner.owner_address.province">, {{ owner.owner_address.province }}</span></div>
                <div v-if="owner.owner_address.postal_code">{{ owner.owner_address.postal_code }}</div>
              </div>
            </div>

            <!-- Representative -->
            <div class="card p-5 space-y-3">
              <div class="text-xs font-semibold uppercase tracking-wide text-navy">Representative</div>

              <div v-if="owner.representative_name" class="space-y-3">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-surface-secondary flex items-center justify-center flex-shrink-0">
                    <span class="text-navy font-bold text-sm">{{ initials(owner.representative_name) }}</span>
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm font-semibold text-gray-900">{{ owner.representative_name }}</div>
                    <div v-if="owner.representative_id_number" class="text-xs text-gray-400">ID: {{ owner.representative_id_number }}</div>
                  </div>
                </div>

                <div class="space-y-1.5 text-xs">
                  <a
                    v-if="owner.representative_phone"
                    :href="`tel:${owner.representative_phone}`"
                    class="flex items-center gap-2 text-gray-600 hover:text-navy"
                  >
                    <Phone :size="12" class="text-gray-400 flex-shrink-0" />
                    {{ owner.representative_phone }}
                  </a>
                  <a
                    v-if="owner.representative_email"
                    :href="`mailto:${owner.representative_email}`"
                    class="flex items-center gap-2 text-gray-600 hover:text-navy truncate"
                  >
                    <Mail :size="12" class="text-gray-400 flex-shrink-0" />
                    {{ owner.representative_email }}
                  </a>
                </div>
              </div>

              <p v-else class="text-xs text-gray-400">No representative assigned.</p>
            </div>
          </div>

          <!-- Bank details -->
          <div v-if="owner.bank_details?.bank_name" class="card p-5 space-y-3">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy">Banking Details</div>
            <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
              <div>
                <div class="text-gray-400">Bank</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ owner.bank_details.bank_name }}</div>
              </div>
              <div>
                <div class="text-gray-400">Account holder</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ owner.bank_details.account_holder || '—' }}</div>
              </div>
              <div>
                <div class="text-gray-400">Account number</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ owner.bank_details.account_number || '—' }}</div>
              </div>
              <div>
                <div class="text-gray-400">Branch code</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ owner.bank_details.branch_code || '—' }}</div>
              </div>
              <div>
                <div class="text-gray-400">Account type</div>
                <div class="font-semibold text-gray-900 mt-0.5 capitalize">{{ owner.bank_details.account_type || '—' }}</div>
              </div>
            </div>
          </div>

          <!-- Ownership period -->
          <div class="card p-5 space-y-3">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy">Ownership</div>
            <div class="grid grid-cols-3 gap-4 text-xs">
              <div>
                <div class="text-gray-400">Since</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ fmtDate(owner.start_date) }}</div>
              </div>
              <div>
                <div class="text-gray-400">Status</div>
                <span :class="owner.is_current ? 'badge-green' : 'badge-gray'">{{ owner.is_current ? 'Current owner' : 'Former owner' }}</span>
              </div>
              <div v-if="owner.end_date">
                <div class="text-gray-400">Until</div>
                <div class="font-semibold text-gray-900 mt-0.5">{{ fmtDate(owner.end_date) }}</div>
              </div>
            </div>
            <div v-if="owner.notes" class="border-t border-gray-100 pt-2.5 text-xs text-gray-600">
              <div class="text-gray-400 text-[10px] uppercase tracking-wide mb-1">Notes</div>
              {{ owner.notes }}
            </div>
          </div>
        </template>

        <EmptyState
          v-else
          title="No owner linked"
          description="Link an owner to this property from the landlords page."
          :icon="Building2"
        >
          <RouterLink to="/landlords" class="btn-primary btn-sm">Manage landlords</RouterLink>
        </EmptyState>
      </div>

      <!-- ── Suppliers tab ── -->
      <div v-else-if="activeSection === 'suppliers'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500">Suppliers linked to this property.</p>
          <RouterLink to="/maintenance/suppliers" class="btn-ghost btn-sm text-navy">
            <Truck :size="14" /> Manage all suppliers
          </RouterLink>
        </div>

        <div v-if="loadingSuppliers" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
          <div v-for="i in 3" :key="i" class="card p-5"><div class="h-28 bg-gray-100 rounded" /></div>
        </div>

        <div v-else-if="propertySuppliers.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="s in propertySuppliers"
            :key="s.id"
            class="card p-5 space-y-3 hover:shadow-md transition-shadow cursor-pointer"
            @click="$router.push(`/maintenance/suppliers/${s.id}`)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-10 h-10 rounded-full bg-surface-secondary flex items-center justify-center flex-shrink-0">
                  <Truck :size="16" class="text-navy" />
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-semibold text-gray-900 truncate">{{ s.display_name || s.company_name || s.name }}</div>
                  <div v-if="s.company_name && s.name !== s.company_name" class="text-xs text-gray-400 truncate">{{ s.name }}</div>
                </div>
              </div>
              <span
                v-if="s.property_links?.some((l: any) => l.property === property?.id && l.is_preferred)"
                class="badge-green text-[10px] flex-shrink-0"
              >Preferred</span>
            </div>

            <div v-if="s.trades?.length" class="flex flex-wrap gap-1">
              <span
                v-for="t in s.trades"
                :key="t.id"
                class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 capitalize"
              >{{ t.trade_display || t.trade }}</span>
            </div>

            <div class="space-y-1.5 text-xs">
              <a
                v-if="s.phone"
                :href="`tel:${s.phone}`"
                class="flex items-center gap-2 text-gray-600 hover:text-navy"
                @click.stop
              >
                <Phone :size="12" class="text-gray-400 flex-shrink-0" />
                {{ s.phone }}
              </a>
              <a
                v-if="s.email"
                :href="`mailto:${s.email}`"
                class="flex items-center gap-2 text-gray-600 hover:text-navy truncate"
                @click.stop
              >
                <Mail :size="12" class="text-gray-400 flex-shrink-0" />
                {{ s.email }}
              </a>
            </div>

            <div v-if="s.active_jobs_count" class="border-t border-gray-100 pt-2 flex items-center gap-1.5">
              <Wrench :size="12" class="text-warning-500" />
              <span class="text-xs text-gray-600">{{ s.active_jobs_count }} active job{{ s.active_jobs_count !== 1 ? 's' : '' }}</span>
            </div>
          </div>
        </div>

        <EmptyState
          v-else
          title="No suppliers linked"
          description="Link suppliers to this property from the suppliers page."
          :icon="Truck"
        >
          <RouterLink to="/maintenance/suppliers" class="btn-primary btn-sm">Manage suppliers</RouterLink>
        </EmptyState>
      </div>

    </template>

    <!-- ── Modals ── -->

    <!-- Add / Edit inventory item -->
    <BaseModal :open="itemModal" :title="editingItem ? 'Edit item' : 'Add inventory item'" @close="itemModal = false">
      <div class="space-y-4">
        <div>
          <label class="label">Name <span class="text-danger-500">*</span></label>
          <input v-model="itemForm.name" class="input" placeholder="e.g. Samsung fridge 350L" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Category</label>
            <select v-model="itemForm.category" class="input">
              <option value="appliance">Appliance</option>
              <option value="furniture">Furniture</option>
              <option value="fixture">Fixture</option>
              <option value="electronics">Electronics</option>
              <option value="linen">Linen / Bedding</option>
              <option value="kitchen">Kitchenware</option>
              <option value="keys">Keys / Remotes</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label class="label">Quantity</label>
            <input v-model.number="itemForm.quantity" type="number" min="1" class="input" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Condition (move-in)</label>
            <select v-model="itemForm.condition_in" class="input">
              <option value="new">New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="poor">Poor</option>
              <option value="damaged">Damaged</option>
            </select>
          </div>
          <div>
            <label class="label">Condition (move-out)</label>
            <select v-model="itemForm.condition_out" class="input">
              <option value="">Not assessed</option>
              <option value="new">New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="poor">Poor</option>
              <option value="damaged">Damaged</option>
              <option value="missing">Missing</option>
            </select>
          </div>
        </div>
        <div>
          <label class="label">Barcode / Serial / Asset tag</label>
          <div class="flex gap-2">
            <input v-model="itemForm.barcode" class="input flex-1 font-mono" placeholder="Scan or type barcode…" />
            <button class="btn-ghost btn-sm" aria-label="Scan barcode" @click="triggerBarcodeScan">
              <ScanBarcode :size="16" />
            </button>
          </div>
        </div>
        <div>
          <label class="label">Notes</label>
          <textarea v-model="itemForm.notes" class="input h-16 resize-none" placeholder="Brand, model, serial number, description…" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Photo (move-in)</label>
            <label class="flex items-center justify-center gap-2 border-2 border-dashed border-gray-200 rounded-lg p-3 cursor-pointer hover:border-navy/30 transition-colors">
              <img v-if="itemPhotoInPreview" :src="itemPhotoInPreview" class="w-16 h-16 rounded object-cover" />
              <template v-else>
                <ImagePlus :size="16" class="text-gray-400" />
                <span class="text-xs text-gray-400">Upload</span>
              </template>
              <input type="file" accept="image/*" class="hidden" @change="onPhotoIn" />
            </label>
          </div>
          <div>
            <label class="label">Photo (move-out)</label>
            <label class="flex items-center justify-center gap-2 border-2 border-dashed border-gray-200 rounded-lg p-3 cursor-pointer hover:border-navy/30 transition-colors">
              <img v-if="itemPhotoOutPreview" :src="itemPhotoOutPreview" class="w-16 h-16 rounded object-cover" />
              <template v-else>
                <ImagePlus :size="16" class="text-gray-400" />
                <span class="text-xs text-gray-400">Upload</span>
              </template>
              <input type="file" accept="image/*" class="hidden" @change="onPhotoOut" />
            </label>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="itemModal = false">Cancel</button>
        <button class="btn-primary" :disabled="savingItem || !itemForm.name" @click="saveItem">
          <Loader2 v-if="savingItem" :size="14" class="animate-spin" />
          {{ editingItem ? 'Update' : 'Add item' }}
        </button>
      </template>
    </BaseModal>

    <!-- Apply inventory template -->
    <BaseModal :open="showTemplateModal" title="Apply inventory template" @close="showTemplateModal = false">
      <div v-if="loadingTemplates" class="space-y-3 animate-pulse">
        <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-lg" />
      </div>
      <div v-else-if="inventoryTemplates.length" class="space-y-2">
        <button
          v-for="tmpl in inventoryTemplates"
          :key="tmpl.id"
          class="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-navy/30 hover:bg-navy/5 transition-colors"
          @click="applyTemplate(tmpl.id)"
        >
          <div class="text-sm font-medium text-gray-900">{{ tmpl.name }}</div>
          <div class="text-xs text-gray-400 mt-0.5">{{ tmpl.item_count }} items</div>
        </button>
      </div>
      <EmptyState v-else title="No templates" description="Create inventory templates from the leases section." :icon="ClipboardList" />
    </BaseModal>

    <!-- Hidden barcode scanner input -->
    <input ref="barcodeInput" type="text" class="fixed -top-20 opacity-0" @keydown.enter="onBarcodeScanned" />

    <BaseModal :open="voidModal" title="Void lease?" @close="voidModal = false">
      <p class="text-sm text-gray-600">
        This will mark the current active lease as <strong>void</strong>. This action cannot be undone.
      </p>
      <template #footer>
        <button class="btn-ghost" @click="voidModal = false">Cancel</button>
        <button class="btn-danger" :disabled="voiding" @click="confirmVoid">
          <Loader2 v-if="voiding" :size="14" class="animate-spin" />
          Void lease
        </button>
      </template>
    </BaseModal>

    <BaseModal :open="renewModal" title="Renew lease — addendum" @close="renewModal = false">
      <div class="space-y-5">
        <div class="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-600 space-y-0.5">
          <div>Current lease: <strong class="text-gray-900">{{ fmtDate(activeLease?.start_date) }} → {{ fmtDate(activeLease?.end_date) }}</strong></div>
          <div>Current rent: <strong class="text-gray-900">R{{ Number(activeLease?.monthly_rent ?? 0).toLocaleString('en-ZA') }}/mo</strong></div>
        </div>
        <div>
          <label class="label">Renewal period</label>
          <div class="grid grid-cols-2 gap-2 mt-1">
            <button class="rounded-xl border-2 p-3 text-left transition-colors" :class="renewMode==='12months'?'border-navy bg-navy/5':'border-gray-200 hover:border-gray-300'" @click="selectRenewMode('12months')">
              <div class="text-sm font-semibold text-gray-900">+12 months</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ renewMode==='12months' ? `→ ${fmtDate(renewEndDate)}` : 'Standard renewal' }}</div>
            </button>
            <button class="rounded-xl border-2 p-3 text-left transition-colors" :class="renewMode==='custom'?'border-navy bg-navy/5':'border-gray-200 hover:border-gray-300'" @click="selectRenewMode('custom')">
              <div class="text-sm font-semibold text-gray-900">Custom period</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ renewMode==='custom' && renewCustomEnd ? `→ ${fmtDate(renewCustomEnd)}` : 'Pick an end date' }}</div>
            </button>
          </div>
          <div v-if="renewMode==='custom'" class="mt-2">
            <input v-model="renewCustomEnd" type="date" class="input" :min="minRenewDate" />
          </div>
        </div>
        <div>
          <label class="label">New monthly rent (ZAR) <span class="text-danger-500">*</span></label>
          <div class="relative mt-1">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">R</span>
            <input v-model="renewRent" type="number" min="0" step="100" class="input pl-7" placeholder="55 000" />
          </div>
          <p v-if="rentDiff !== 0" class="text-xs mt-1" :class="rentDiff>0?'text-success-600':'text-danger-500'">
            {{ rentDiff > 0 ? '▲' : '▼' }} R{{ Math.abs(rentDiff).toLocaleString('en-ZA') }}/mo ({{ rentDiffPct }}% {{ rentDiff > 0 ? 'increase' : 'decrease' }})
          </p>
        </div>
        <div>
          <label class="label">Addendum notes <span class="text-gray-400 font-normal normal-case">(optional)</span></label>
          <textarea v-model="renewNotes" class="input h-16 resize-none mt-1" placeholder="Any special conditions for this renewal period…" />
        </div>
        <div v-if="renewEndDate" class="rounded-lg border border-navy/20 bg-navy/5 px-4 py-3 text-xs text-gray-700 space-y-1">
          <div class="font-semibold text-navy text-[11px] uppercase tracking-wide mb-1.5">Addendum summary</div>
          <div>Period: <strong>{{ fmtDate(activeLease?.end_date) }} → {{ fmtDate(renewEndDate) }}</strong></div>
          <div>Rent: <strong>R{{ Number(renewRent || 0).toLocaleString('en-ZA') }}/mo</strong></div>
          <div v-if="renewNotes" class="text-gray-500 italic">{{ renewNotes }}</div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="renewModal = false">Cancel</button>
        <button class="btn-primary" :disabled="renewing || !renewEndDate || !renewRent" @click="confirmRenew">
          <Loader2 v-if="renewing" :size="14" class="animate-spin" />
          Create addendum
        </button>
      </template>
    </BaseModal>

    <ConfirmDialog
      :open="deletePhotoOpen"
      title="Delete photo?"
      description="This photo will be permanently removed."
      confirm-label="Delete"
      :loading="deletePhotoBusy"
      @confirm="doDeletePhoto"
      @cancel="deletePhotoOpen = false; deletingPhoto = null"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { usePropertiesStore } from '../../stores/properties'
import { useLeasesStore } from '../../stores/leases'
import { useOwnershipsStore } from '../../stores/ownerships'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import BaseModal from '../../components/BaseModal.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import MandateTab from './MandateTab.vue'
import {
  ArrowLeft, MoreHorizontal, FilePlus2, Ban, Upload, FileText,
  FileSignature, Loader2, Calendar, Wrench, Phone, Mail, ImagePlus,
  ClipboardList, ListTodo, Plus, ScanBarcode, FolderOpen,
  Megaphone, Building2, Landmark, ShieldCheck, Cpu, Receipt, Zap, Truck,
  Home, CheckCircle, X, ChevronRight,
} from 'lucide-vue-next'

const NOTICE_DAYS = 30

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const toast  = useToast()
const propertiesStore = usePropertiesStore()
const leasesStore = useLeasesStore()
const ownershipsStore = useOwnershipsStore()

// ── State ──
const loading          = ref(true)
const property         = ref<any>(null)
const owner            = ref<any>(null)
const linkedTemplate   = ref<any>(null)
const activeLease      = ref<any>(null)
const openMaintenance  = ref<any[]>([])
const unitPhotos       = ref<any[]>([])
const loadingOwner     = ref(false)
const loadingTemplate  = ref(false)
const loadingLease     = ref(false)
const loadingMaintenance = ref(false)
const currentLeases     = ref<any[]>([])
const previousLeases    = ref<any[]>([])
const loadingPrevLeases = ref(false)
const propertySuppliers = ref<any[]>([])
const loadingSuppliers  = ref(false)
const loadingPhotos    = ref(false)
const uploadingPhotos  = ref(false)
const uploadProgress   = ref(0)

// Photo deletion confirm dialog
const deletePhotoOpen   = ref(false)
const deletingPhoto     = ref<any>(null)
const deletePhotoBusy   = ref(false)

// Overview dashboard data
const complianceCerts    = ref<any[]>([])
const loadingCompliance  = ref(false)

const menuOpen   = ref(false)
const menuRef    = ref<HTMLElement | null>(null)
const activeUnit = ref<number | null>(null)
const activeSection = ref<'overview' | 'leases' | 'mandate' | 'inventory' | 'maintenance' | 'advertising' | 'landlord' | 'documentation' | 'suppliers'>('overview')

const sectionTabs = computed(() => {
  const tabs: Array<{ key: string; label: string; icon: any }> = [
    { key: 'overview', label: 'Overview', icon: Wrench },
    { key: 'leases',   label: 'Leases',   icon: FileSignature },
  ]
  if (auth.isAgency) {
    tabs.push({ key: 'mandate', label: 'Mandate', icon: FileSignature })
  }
  tabs.push(
    { key: 'landlord', label: 'Landlord', icon: Building2 },
    { key: 'documentation', label: 'Documentation', icon: FolderOpen },
    { key: 'inventory', label: 'Inventory', icon: ClipboardList },
    { key: 'suppliers', label: 'Suppliers', icon: Truck },
    { key: 'advertising', label: 'Advertising', icon: Megaphone },
    { key: 'maintenance', label: 'Maintenance & Tasks', icon: ListTodo },
  )
  return tabs
})

const adDescription = ref('')
const adSaved       = ref(false)
let adSavedTimer: ReturnType<typeof setTimeout>

// ── Documentation state ──
const propertyDocs  = ref<any[]>([])
const loadingDocs   = ref(false)
const houseRules    = ref('')
const rulesSaved    = ref(false)
let rulesSavedTimer: ReturnType<typeof setTimeout>

const docCategories = [
  { key: 'purchase', label: 'Purchase & Transfer', icon: Landmark, types: ['offer_to_purchase', 'title_deed', 'transfer_docs', 'valuation'], desc: 'Offer to purchase, title deed, transfer duty receipt, property valuation' },
  { key: 'compliance', label: 'Compliance Certificates', icon: ShieldCheck, types: ['compliance_cert', 'electrical_coc', 'gas_coc', 'plumbing_coc', 'beetle_cert', 'fence_cert'], desc: 'Electrical CoC, gas compliance, plumbing, beetle, electric fence' },
  { key: 'municipal', label: 'Municipal & Rates', icon: Receipt, types: ['municipal', 'rates_clearance', 'zoning_cert', 'building_plans'], desc: 'Rates clearance, municipal bills, zoning certificate, approved building plans' },
  { key: 'technical', label: 'Technical & Handover', icon: Cpu, types: ['technical_drawing', 'dev_handover', 'warranty', 'paint_spec', 'generator', 'solar'], desc: 'Warranties, paint specs, generator/solar docs, developer handover pack' },
  { key: 'insurance', label: 'Bond, Finance & Insurance', icon: Zap, types: ['insurance', 'bond_docs', 'capital_upgrade', 'sars_docs', 'finance_costs'], desc: 'Bond/mortgage docs, SARS tax certificates, financing costs, building insurance, capital upgrades' },
  { key: 'estate', label: 'Estate & Body Corporate', icon: FolderOpen, types: ['estate_rules', 'body_corporate', 'hoa_levy'], desc: 'Sectional title rules, body corporate minutes, HOA levy statements' },
  { key: 'other', label: 'Other', icon: FileText, types: ['other', 'house_rules'], desc: 'Any other property-related documents' },
]

const docsByCategory = computed(() => {
  const grouped: Record<string, any[]> = {}
  for (const cat of docCategories) {
    grouped[cat.key] = propertyDocs.value.filter(d => cat.types.includes(d.doc_type))
  }
  return grouped
})

// ── Inventory state ──
const inventoryItems     = ref<any[]>([])
const inventoryTemplates = ref<any[]>([])
const loadingInventory   = ref(false)
const loadingTemplates   = ref(false)
const itemModal          = ref(false)
const showTemplateModal  = ref(false)
const savingItem         = ref(false)
const editingItem        = ref<any>(null)
const barcodeInput       = ref<HTMLInputElement | null>(null)
const itemPhotoInPreview = ref('')
const itemPhotoOutPreview = ref('')
let itemPhotoInFile: File | null = null
let itemPhotoOutFile: File | null = null

const itemForm = ref({
  name: '',
  category: 'other',
  quantity: 1,
  barcode: '',
  notes: '',
  condition_in: 'good',
  condition_out: '',
})

const voidModal   = ref(false)
const voiding     = ref(false)
const renewModal  = ref(false)
const renewing    = ref(false)
const renewMode   = ref<'12months' | 'custom'>('12months')
const renewCustomEnd = ref('')
const renewRent   = ref<number | ''>('')
const renewNotes  = ref('')

// ── Computed ──
const activeUnitData = computed(() =>
  property.value?.units?.find((u: any) => u.id === activeUnit.value) ?? null
)

const daysToExpiry = computed(() => {
  if (!activeLease.value?.end_date) return 0
  return Math.max(0, Math.ceil((new Date(activeLease.value.end_date).getTime() - Date.now()) / 86400000))
})

const noticeDeadline = computed((): string => {
  if (!activeLease.value?.end_date) return ''
  const d = new Date(activeLease.value.end_date)
  d.setDate(d.getDate() - NOTICE_DAYS)
  return d.toISOString().slice(0, 10)
})

const daysToNotice = computed(() =>
  noticeDeadline.value
    ? Math.ceil((new Date(noticeDeadline.value).getTime() - Date.now()) / 86400000)
    : 0
)

const leasePct = computed(() => {
  const l = activeLease.value
  if (!l?.start_date || !l?.end_date) return 0
  const start = new Date(l.start_date).getTime()
  const end   = new Date(l.end_date).getTime()
  return Math.min(100, Math.max(0, Math.round(((Date.now() - start) / (end - start)) * 100)))
})

const noticeDeadlinePct = computed(() => {
  const l = activeLease.value
  if (!l?.start_date || !l?.end_date || !noticeDeadline.value) return 0
  const start = new Date(l.start_date).getTime()
  const end   = new Date(l.end_date).getTime()
  const nd    = new Date(noticeDeadline.value).getTime()
  return Math.min(100, Math.max(0, Math.round(((nd - start) / (end - start)) * 100)))
})

const leaseUrgency = computed((): 'ok' | 'warning' | 'critical' => {
  const d = daysToExpiry.value
  if (d <= 30) return 'critical'
  if (d <= 90) return 'warning'
  return 'ok'
})

const leaseMonths = computed(() => {
  const l = activeLease.value
  if (!l?.start_date || !l?.end_date) return []
  const start = new Date(l.start_date)
  const end   = new Date(l.end_date)
  const now   = new Date()
  const nd    = noticeDeadline.value ? new Date(noticeDeadline.value) : null
  const renewalStart = l.renewal_start_date ? new Date(l.renewal_start_date) : null
  const months: { label: string; state: string }[] = []
  const cur = new Date(start.getFullYear(), start.getMonth(), 1)
  while (cur <= end) {
    const isElapsed = cur < new Date(now.getFullYear(), now.getMonth(), 1)
    const isCurrent = cur.getFullYear() === now.getFullYear() && cur.getMonth() === now.getMonth()
    const isRenewal = renewalStart ? cur >= new Date(renewalStart.getFullYear(), renewalStart.getMonth(), 1) : false
    const isNotice  = nd ? (cur >= new Date(nd.getFullYear(), nd.getMonth(), 1) && !isElapsed && !isCurrent && !isRenewal) : false
    months.push({
      label: cur.toLocaleString('en-ZA', { month: 'long', year: 'numeric' }),
      state: isCurrent ? 'current' : isElapsed ? 'elapsed' : isRenewal ? 'renewal' : isNotice ? 'notice' : 'future',
    })
    cur.setMonth(cur.getMonth() + 1)
  }
  return months
})

const totalLeaseMonths = computed(() => leaseMonths.value.length)
const monthsElapsed    = computed(() => leaseMonths.value.filter(m => m.state === 'elapsed').length)
const monthsRenewal    = computed(() => leaseMonths.value.filter(m => m.state === 'renewal').length)
const monthsRemaining  = computed(() => leaseMonths.value.filter(m => ['future', 'notice', 'renewal'].includes(m.state)).length)

const totalRentCommitted = computed(() =>
  (Number(activeLease.value?.monthly_rent ?? 0) * totalLeaseMonths.value)
    .toLocaleString('en-ZA', { maximumFractionDigits: 0 })
)
const rentReceived = computed(() =>
  (Number(activeLease.value?.monthly_rent ?? 0) * monthsElapsed.value)
    .toLocaleString('en-ZA', { maximumFractionDigits: 0 })
)

const leaseMilestones = computed(() => {
  const l = activeLease.value
  if (!l) return []
  const now = new Date()
  const todayStr = now.toISOString().slice(0, 10)
  const ms: { label: string; date: string; dotClass: string; note?: string; noteClass?: string; isToday?: boolean }[] = []

  ms.push({
    label: 'Contract start',
    date: l.start_date,
    dotClass: 'bg-navy border-navy',
    note: `${monthsElapsed.value} months elapsed`,
    noteClass: 'text-gray-400',
  })

  ms.push({
    label: 'Today',
    date: todayStr,
    dotClass: 'bg-white border-navy',
    isToday: true,
    note: `${monthsRemaining.value} months remaining`,
    noteClass: 'text-gray-500',
  })

  if (noticeDeadline.value && noticeDeadline.value > todayStr) {
    ms.push({
      label: 'Notice deadline',
      date: noticeDeadline.value,
      dotClass: daysToNotice.value <= 14 ? 'bg-danger-200 border-danger-400' : 'bg-warning-100 border-warning-400',
      note: daysToNotice.value <= 0 ? 'Overdue — renew now' : `${daysToNotice.value} days to give notice`,
      noteClass: daysToNotice.value <= 14 ? 'text-danger-500 font-medium' : 'text-warning-600',
    })
  }

  if (l.renewal_start_date) {
    ms.push({
      label: 'Renewal start (unsigned)',
      date: l.renewal_start_date,
      dotClass: 'bg-amber-100 border-amber-400',
      note: 'Addendum pending signature',
      noteClass: 'text-amber-600',
    })
  }

  ms.push({
    label: daysToExpiry.value <= 0 ? 'Expired' : 'Contract end',
    date: l.end_date,
    dotClass: leaseUrgency.value === 'critical' ? 'bg-danger-100 border-danger-500' : 'bg-gray-100 border-gray-300',
    note: daysToExpiry.value > 0 ? fmtDate(l.end_date) : undefined,
    noteClass: 'text-gray-400',
  })

  return ms.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
})

const minRenewDate = computed(() => {
  if (!activeLease.value?.end_date) return today()
  const d = new Date(activeLease.value.end_date)
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
})

const renewEndDate = computed(() => {
  if (renewMode.value === '12months') {
    if (!activeLease.value?.end_date) return ''
    const d = new Date(activeLease.value.end_date)
    d.setFullYear(d.getFullYear() + 1)
    return d.toISOString().slice(0, 10)
  }
  return renewCustomEnd.value
})

const rentDiff = computed(() =>
  Number(renewRent.value || 0) - Number(activeLease.value?.monthly_rent ?? 0)
)
const rentDiffPct = computed(() => {
  const old = Number(activeLease.value?.monthly_rent ?? 0)
  return old ? Math.abs(Math.round((rentDiff.value / old) * 100)).toString() : '0'
})

// ── Overview dashboard computed ──
const totalUnits = computed(() => property.value?.units?.length ?? 0)
const occupiedUnits = computed(() =>
  property.value?.units?.filter((u: any) => u.status === 'occupied').length ?? 0
)
const totalMonthlyIncome = computed(() =>
  property.value?.units
    ?.filter((u: any) => u.active_lease_info)
    .reduce((sum: number, u: any) => sum + Number(u.active_lease_info.monthly_rent ?? 0), 0) ?? 0
)
const complianceByType = computed(() => {
  const map: Record<string, any> = {}
  for (const cert of complianceCerts.value) {
    if (!map[cert.cert_type]) map[cert.cert_type] = cert
  }
  return Object.values(map)
})

// ── Load data ──
async function initProperty(id: number) {
  // Reset state for new property
  property.value = null
  activeUnit.value = null
  activeSection.value = 'overview'
  owner.value = null
  activeLease.value = null
  currentLeases.value = []
  previousLeases.value = []
  unitPhotos.value = []
  propertyDocs.value = []
  openMaintenance.value = []
  propertySuppliers.value = []
  inventoryItems.value = []

  loading.value = true
  try {
    const data = await propertiesStore.fetchOne(id, { force: true })
    property.value = data
    if (data.units?.length) {
      activeUnit.value = data.units[0].id
      adDescription.value = data.units[0].ad_description ?? ''
    } else {
      adDescription.value = data.description ?? ''
    }
  } catch {
    toast.error('Property not found')
    router.push('/properties')
    return
  } finally {
    loading.value = false
  }

  const pid = property.value.id

  // Parallel background loads
  loadingOwner.value = true
  ownershipsStore.fetchCurrent(pid)
    .then(o => { owner.value = o })
    .catch(() => {})
    .finally(() => { loadingOwner.value = false })

  loadingTemplate.value = true
  api.get('/leases/templates/', { params: { property: pid, page_size: 1 } })
    .then(r => { linkedTemplate.value = (r.data.results ?? r.data)[0] ?? null })
    .catch(() => {})
    .finally(() => { loadingTemplate.value = false })

  loadingMaintenance.value = true
  api.get('/maintenance/', { params: { property: pid, status: 'open', page_size: 5 } })
    .then(r => { openMaintenance.value = r.data.results ?? r.data })
    .catch(() => {})
    .finally(() => { loadingMaintenance.value = false })

  if (activeUnit.value) loadUnitLeases(activeUnit.value)
  loadPhotos(pid, activeUnit.value)  // null = property-level photos (no unit)

  loadDocs(pid)
  houseRules.value = property.value.house_rules ?? ''

  loadOverviewData(pid)
}

onMounted(() => {
  initProperty(Number(route.params.id))
  document.addEventListener('mousedown', onOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onOutsideClick)
  clearTimeout(adSavedTimer)
  clearTimeout(rulesSavedTimer)
})

// Re-init when navigating between different properties (KeepAlive reuses the instance).
// Only fire when we're actually on the property-detail route — otherwise navigating to
// /landlords/:id would also trigger this watcher and try to load the landlord id as a property.
watch(() => route.params.id, (newId, oldId) => {
  if (route.name !== 'property-detail') return
  if (newId && newId !== oldId) initProperty(Number(newId))
})

// Reload lease + photos when unit tab changes
watch(activeUnit, (unitId) => {
  if (!unitId || !property.value) return
  const unit = property.value.units.find((u: any) => u.id === unitId)
  adDescription.value = unit?.ad_description ?? ''

  loadPhotos(property.value.id, unitId)
  loadUnitLeases(unitId)
})

// Load inventory when switching to inventory tab or when lease changes
watch(activeSection, (sec) => {
  if (sec === 'inventory' && activeLease.value && !inventoryItems.value.length && !loadingInventory.value) {
    loadInventory()
  }
  if (sec === 'inventory' && !inventoryTemplates.value.length) {
    loadInventoryTemplates()
  }
  if (sec === 'suppliers' && !loadingSuppliers.value) {
    loadSuppliers()
  }
})

watch(activeLease, () => {
  inventoryItems.value = []
  if (activeSection.value === 'inventory' && activeLease.value) loadInventory()
})

function switchUnit(unitId: number) {
  activeUnit.value = unitId
}

function daysUntil(isoDate: string): number {
  return Math.max(0, Math.ceil((new Date(isoDate).getTime() - Date.now()) / 86400000))
}

function loadUnitLeases(unitId: number) {
  loadingPrevLeases.value = true
  loadingLease.value = true
  leasesStore.fetchForUnit(unitId)
    .then(all => {
      const CURRENT = new Set(['active', 'pending'])
      currentLeases.value  = all.filter((l: any) => CURRENT.has(l.status))
      previousLeases.value = all.filter((l: any) => !CURRENT.has(l.status))
      activeLease.value    = currentLeases.value[0] ?? null
    })
    .catch(() => { activeLease.value = null })
    .finally(() => {
      loadingPrevLeases.value = false
      loadingLease.value = false
    })
}

function loadPhotos(propertyId: number, unitId: number | null) {
  loadPhotosAsync(propertyId, unitId)
}

function onOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) menuOpen.value = false
}

// ── Advertising ──
async function saveAdDescription() {
  if (!property.value) return
  try {
    if (activeUnit.value) {
      const updated = await propertiesStore.updateUnit(activeUnit.value, property.value.id, { ad_description: adDescription.value })
      property.value = updated
    } else {
      const updated = await propertiesStore.update(property.value.id, { description: adDescription.value })
      property.value = updated
    }
    adSaved.value = true
    clearTimeout(adSavedTimer)
    adSavedTimer = setTimeout(() => { adSaved.value = false }, 2000)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save description'))
  }
}

async function uploadPhotos(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length || !property.value) return
  const fd = new FormData()
  Array.from(files).forEach(f => fd.append('photo', f))
  if (activeUnit.value) fd.append('unit', String(activeUnit.value))
  uploadingPhotos.value = true
  uploadProgress.value = 0
  try {
    await api.post(`/properties/${property.value.id}/photos/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt: any) => {
        if (evt.total) {
          // Cap at 85% — remaining 15% reserved for server processing + reload
          uploadProgress.value = Math.min(85, Math.round((evt.loaded * 100) / evt.total))
        } else {
          uploadProgress.value = 40
        }
      },
    })
    // Show "processing" phase while server generates thumbnails
    uploadProgress.value = 90
    await loadPhotosAsync(property.value.id, activeUnit.value)
    uploadProgress.value = 100
    toast.success('Photos uploaded')
  } catch {
    toast.error('Failed to upload photos')
  } finally {
    uploadingPhotos.value = false
    uploadProgress.value = 0
    input.value = ''
  }
}

function deletePhoto(photo: any) {
  deletingPhoto.value = photo
  deletePhotoOpen.value = true
}

async function doDeletePhoto() {
  if (!deletingPhoto.value) return
  deletePhotoBusy.value = true
  try {
    await api.delete(`/properties/${property.value!.id}/photos/${deletingPhoto.value.id}/`)
    unitPhotos.value = unitPhotos.value.filter(p => p.id !== deletingPhoto.value.id)
    deletePhotoOpen.value = false
    deletingPhoto.value = null
    toast.success('Photo deleted')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete photo'))
  } finally {
    deletePhotoBusy.value = false
  }
}

function loadPhotosAsync(propertyId: number, unitId: number | null): Promise<void> {
  // Only show skeleton on initial load — keep existing photos visible during refreshes
  if (!unitPhotos.value.length) loadingPhotos.value = true
  const params = unitId ? { unit: unitId } : {}
  return api.get(`/properties/${propertyId}/photos/`, { params })
    .then(r => { unitPhotos.value = r.data.results ?? r.data })
    .catch(() => { toast.error('Failed to load photos') })
    .finally(() => { loadingPhotos.value = false })
}

// ── Documents & House Rules ──
function loadDocs(propertyId: number) {
  loadingDocs.value = true
  api.get(`/properties/${propertyId}/documents/`)
    .then(r => { propertyDocs.value = r.data.results ?? r.data })
    .catch(() => {})
    .finally(() => { loadingDocs.value = false })
}

async function uploadDocument(e: Event, docType = 'other') {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !property.value) return
  const fd = new FormData()
  fd.append('document', file)
  fd.append('doc_type', docType)
  try {
    await api.post(`/properties/${property.value.id}/documents/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    loadDocs(property.value.id)
    toast.success('Document uploaded')
  } catch {
    toast.error('Failed to upload document')
  }
  (e.target as HTMLInputElement).value = ''
}

function uploadDocWithType(e: Event) { uploadDocument(e, 'other') }
function uploadDocForCategory(e: Event, docType: string) { uploadDocument(e, docType) }

async function saveHouseRules() {
  if (!property.value) return
  try {
    const updated = await propertiesStore.update(property.value.id, { house_rules: houseRules.value })
    property.value = updated
    rulesSaved.value = true
    clearTimeout(rulesSavedTimer)
    rulesSavedTimer = setTimeout(() => { rulesSaved.value = false }, 2000)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save house rules'))
  }
}

// ── Inventory ──
function loadInventory() {
  if (!activeLease.value) return
  loadingInventory.value = true
  api.get(`/leases/${activeLease.value.id}/inventory/`)
    .then(r => { inventoryItems.value = r.data.results ?? r.data })
    .catch(() => { toast.error('Failed to load inventory') })
    .finally(() => { loadingInventory.value = false })
}

function loadInventoryTemplates() {
  loadingTemplates.value = true
  api.get('/leases/inventory-templates/')
    .then(r => { inventoryTemplates.value = r.data.results ?? r.data })
    .catch(() => {})
    .finally(() => { loadingTemplates.value = false })
}

function loadSuppliers() {
  if (!property.value) return
  if (!propertySuppliers.value.length) loadingSuppliers.value = true
  api.get('/maintenance/suppliers/', { params: { property: property.value.id } })
    .then(r => { propertySuppliers.value = r.data.results ?? r.data })
    .catch(() => { toast.error('Failed to load suppliers') })
    .finally(() => { loadingSuppliers.value = false })
}

function loadOverviewData(propertyId: number) {
  loadingCompliance.value = true
  api.get('/properties/compliance-certs/', { params: { property: propertyId } })
    .then(r => { complianceCerts.value = r.data.results ?? r.data })
    .catch(() => {})
    .finally(() => { loadingCompliance.value = false })
}

function resetItemForm() {
  itemForm.value = { name: '', category: 'other', quantity: 1, barcode: '', notes: '', condition_in: 'good', condition_out: '' }
  itemPhotoInFile = null
  itemPhotoOutFile = null
  itemPhotoInPreview.value = ''
  itemPhotoOutPreview.value = ''
}

function openAddItem() {
  editingItem.value = null
  resetItemForm()
  itemModal.value = true
}

function editItem(item: any) {
  editingItem.value = item
  itemForm.value = {
    name: item.name,
    category: item.category,
    quantity: item.quantity,
    barcode: item.barcode || '',
    notes: item.notes || '',
    condition_in: item.condition_in,
    condition_out: item.condition_out || '',
  }
  itemPhotoInPreview.value = item.photo_in || ''
  itemPhotoOutPreview.value = item.photo_out || ''
  itemPhotoInFile = null
  itemPhotoOutFile = null
  itemModal.value = true
}

async function saveItem() {
  if (!activeLease.value || !itemForm.value.name) return
  savingItem.value = true
  const fd = new FormData()
  fd.append('name', itemForm.value.name)
  fd.append('category', itemForm.value.category)
  fd.append('quantity', String(itemForm.value.quantity))
  fd.append('barcode', itemForm.value.barcode)
  fd.append('notes', itemForm.value.notes)
  fd.append('condition_in', itemForm.value.condition_in)
  fd.append('condition_out', itemForm.value.condition_out)
  if (itemPhotoInFile) fd.append('photo_in', itemPhotoInFile)
  if (itemPhotoOutFile) fd.append('photo_out', itemPhotoOutFile)

  try {
    if (editingItem.value) {
      await api.patch(`/leases/${activeLease.value.id}/inventory/${editingItem.value.id}/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      toast.success('Item updated')
    } else {
      fd.append('lease', String(activeLease.value.id))
      await api.post(`/leases/${activeLease.value.id}/inventory/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      toast.success('Item added')
    }
    itemModal.value = false
    loadInventory()
  } catch {
    toast.error('Failed to save item')
  } finally {
    savingItem.value = false
  }
}

async function deleteInventoryItem(item: any) {
  if (!activeLease.value) return
  try {
    await api.delete(`/leases/${activeLease.value.id}/inventory/${item.id}/`)
    inventoryItems.value = inventoryItems.value.filter(i => i.id !== item.id)
    toast.success('Item removed')
  } catch {
    toast.error('Failed to delete item')
  }
}

async function applyTemplate(templateId: number) {
  if (!activeLease.value) return
  try {
    await api.post(`/leases/${activeLease.value.id}/inventory/from-template/`, { template_id: templateId })
    showTemplateModal.value = false
    loadInventory()
    toast.success('Template applied')
  } catch {
    toast.error('Failed to apply template')
  }
}

function onPhotoIn(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  itemPhotoInFile = file
  itemPhotoInPreview.value = URL.createObjectURL(file)
}

function onPhotoOut(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  itemPhotoOutFile = file
  itemPhotoOutPreview.value = URL.createObjectURL(file)
}

function triggerBarcodeScan() {
  barcodeInput.value?.focus()
}

function onBarcodeScanned(e: KeyboardEvent) {
  const val = (e.target as HTMLInputElement).value.trim()
  if (val) {
    itemForm.value.barcode = val
    ;(e.target as HTMLInputElement).value = ''
  }
}

function conditionBadge(cond: string): string {
  const map: Record<string, string> = {
    new: 'badge-green',
    good: 'badge-green',
    fair: 'badge-amber',
    poor: 'badge-red',
    damaged: 'badge-red',
    missing: 'badge-red',
  }
  return `${map[cond] || 'badge-gray'} text-[10px]`
}

// ── Renew lease ──
function openRenewModal() {
  if (!activeLease.value) { toast.error('No active lease to renew'); return }
  renewMode.value = '12months'
  renewCustomEnd.value = minRenewDate.value
  renewRent.value = Number(activeLease.value.monthly_rent ?? 0)
  renewNotes.value = ''
  renewModal.value = true
}

function selectRenewMode(mode: '12months' | 'custom') {
  renewMode.value = mode
  if (mode === 'custom') renewCustomEnd.value = minRenewDate.value
}

async function confirmRenew() {
  if (!renewEndDate.value || !renewRent.value || !activeLease.value) return
  renewing.value = true
  const currentEnd = new Date(activeLease.value.end_date)
  currentEnd.setDate(currentEnd.getDate() + 1)
  const renewalStart = currentEnd.toISOString().slice(0, 10)
  try {
    const data = await leasesStore.update(activeLease.value.id, {
      end_date: renewEndDate.value,
      monthly_rent: String(renewRent.value),
      renewal_start_date: renewalStart,
    })
    activeLease.value = {
      ...activeLease.value,
      end_date: data.end_date ?? renewEndDate.value,
      monthly_rent: data.monthly_rent ?? renewRent.value,
      renewal_start_date: data.renewal_start_date ?? renewalStart,
    }
    renewModal.value = false
    toast.success(`Lease renewed to ${fmtDate(renewEndDate.value)} at R${Number(renewRent.value).toLocaleString('en-ZA')}/mo`)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to create renewal addendum'))
  } finally {
    renewing.value = false
  }
}

// ── Other actions ──
function goCreateLease() {
  if (!property.value?.id) {
    router.push('/leases/build')
    return
  }
  const query: Record<string, string | number> = { property: property.value.id }
  if (activeUnit.value) query.unit = activeUnit.value
  router.push({ path: '/leases/build', query })
}

function handleGenerateLease() {
  menuOpen.value = false
  router.push({ path: '/leases/build', query: { property: property.value?.id } })
}


function handleVoidLease() {
  menuOpen.value = false
  if (!activeLease.value) { toast.error('No active lease to void'); return }
  voidModal.value = true
}

function handleAdvertise() {
  menuOpen.value = false
  toast.info('Advertising feature coming soon')
}

function handleArchive() {
  menuOpen.value = false
  toast.info('Archive feature coming soon')
}

async function confirmVoid() {
  voiding.value = true
  try {
    await leasesStore.update(activeLease.value.id, { status: 'terminated' as any })
    activeLease.value = null
    voidModal.value = false
    toast.success('Lease voided')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to void lease'))
  } finally {
    voiding.value = false
  }
}


// ── Helpers ──
function initials(name: string): string {
  if (!name) return '?'
  return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-ZA', { dateStyle: 'medium' })
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

const nextPaymentDate = computed(() => {
  const day = activeLease.value?.rent_due_day || 1
  const now = new Date()
  let next = new Date(now.getFullYear(), now.getMonth(), day)
  if (next <= now) next.setMonth(next.getMonth() + 1)
  return fmtDate(next.toISOString().slice(0, 10))
})

const daysToNextPayment = computed(() => {
  const day = activeLease.value?.rent_due_day || 1
  const now = new Date()
  let next = new Date(now.getFullYear(), now.getMonth(), day)
  if (next <= now) next.setMonth(next.getMonth() + 1)
  return Math.ceil((next.getTime() - now.getTime()) / 86400000)
})
</script>

<style scoped>
.label { @apply text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-0.5; }
.menu-item {
  @apply w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-gray-700
         hover:bg-gray-50 transition-colors text-left;
}
.unit-tab {
  @apply flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 border-transparent
         text-gray-500 hover:text-gray-800 transition-colors whitespace-nowrap cursor-pointer;
}
.unit-tab-active { @apply border-navy text-navy; }
</style>
