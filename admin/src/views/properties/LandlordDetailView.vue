<template>
  <div class="space-y-0">

    <!-- ── Page header ── -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          aria-label="Back to owners"
          @click="$router.push('/landlords')"
        >
          <ArrowLeft :size="18" />
        </button>
        <div>
          <h2 class="text-lg font-semibold text-gray-900">{{ landlord?.name ?? '…' }}</h2>
          <p class="text-xs text-gray-500 mt-0.5">{{ landlord?.email || 'No email' }}</p>
        </div>
      </div>

      <!-- Actions dropdown -->
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
            <button class="menu-item" @click="menuOpen = false; activeTab = 'bank'">
              <Landmark :size="15" class="text-gray-400" /> Add bank account
            </button>
            <div class="my-1 border-t border-gray-100" />
            <button class="menu-item text-danger-500 hover:bg-danger-50" @click="confirmDelete">
              <Trash2 :size="15" /> Delete owner
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <!-- ── Tabs ── -->
    <div class="flex items-center gap-1 border-b border-gray-200 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === tab.key
          ? 'border-navy text-navy'
          : 'border-transparent text-gray-400 hover:text-gray-600 hover:border-gray-300'"
        @click="activeTab = tab.key"
      >
        <component :is="tab.icon" :size="15" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4 animate-pulse">
      <div class="h-12 bg-gray-100 rounded-xl" />
      <div class="h-56 bg-gray-100 rounded-xl" />
    </div>

    <!-- ── Tab: Details ── -->
    <div v-else-if="activeTab === 'details'" class="grid grid-cols-3 gap-6 pt-6">
      <div class="col-span-2 space-y-6">
        <!-- Info card -->
        <div class="card p-5">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center"
              :class="landlord?.landlord_type === 'company' ? 'bg-info-50 text-info-600' : landlord?.landlord_type === 'trust' ? 'bg-purple-100 text-purple-600' : landlord?.landlord_type === 'cc' ? 'bg-warning-50 text-warning-600' : landlord?.landlord_type === 'partnership' ? 'bg-success-50 text-success-600' : 'bg-gray-100 text-gray-600'"
            >
              <Building2 v-if="landlord?.landlord_type === 'company'" :size="22" />
              <Shield v-else-if="landlord?.landlord_type === 'trust'" :size="22" />
              <Briefcase v-else-if="landlord?.landlord_type === 'cc'" :size="22" />
              <Users v-else-if="landlord?.landlord_type === 'partnership'" :size="22" />
              <User v-else :size="22" />
            </div>
            <div>
              <div class="font-semibold text-gray-900">{{ landlord?.name }}</div>
              <span class="badge-gray capitalize text-xs">{{ landlord?.landlord_type }}</span>
            </div>
          </div>

          <form @submit.prevent="saveLandlord" class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div class="col-span-2">
                <label class="label">Legal name</label>
                <input v-model="local.name" class="input" />
              </div>
              <div>
                <label class="label">Type</label>
                <select v-model="local.landlord_type" class="input">
                  <option value="individual">Individual</option>
                  <option value="company">Company (Pty Ltd / NPC)</option>
                  <option value="trust">Trust</option>
                  <option value="cc">Close Corporation (CC)</option>
                  <option value="partnership">Partnership</option>
                </select>
              </div>
              <div v-if="local.landlord_type === 'company' || local.landlord_type === 'cc'" class="col-span-2">
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <input type="checkbox" v-model="local.owned_by_trust" class="rounded text-navy" />
                  <span class="text-sm text-gray-700">This entity is wholly or partly owned by a Trust</span>
                </label>
                <p class="text-xs text-gray-400 mt-1 ml-5">Enables FICA trust document requirements for beneficial ownership tracing.</p>
              </div>
              <div>
                <label class="label">{{ local.landlord_type === 'individual' ? 'SA ID / Passport' : 'Registration no.' }}</label>
                <input v-model="local.registration_number" class="input font-mono" />
              </div>
              <div>
                <label class="label">Email</label>
                <input v-model="local.email" type="email" class="input" />
              </div>
              <div>
                <label class="label">Phone</label>
                <input v-model="local.phone" class="input" />
              </div>
              <div v-if="local.landlord_type !== 'individual'">
                <label class="label">VAT number</label>
                <input v-model="local.vat_number" class="input font-mono" />
              </div>
            </div>
            <button type="submit" class="btn-primary text-sm" :disabled="saving">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              Save Changes
            </button>
          </form>
        </div>

        <!-- Representative -->
        <div class="card p-5 space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Representative (signs leases)</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Name</label>
              <input v-model="local.representative_name" class="input" />
            </div>
            <div>
              <label class="label">ID number</label>
              <input v-model="local.representative_id_number" class="input font-mono" />
            </div>
            <div>
              <label class="label">Email</label>
              <input v-model="local.representative_email" type="email" class="input" />
            </div>
            <div>
              <label class="label">Phone</label>
              <input v-model="local.representative_phone" class="input" />
            </div>
          </div>
          <button class="btn-primary text-sm" :disabled="saving" @click="saveLandlord">
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            Save Changes
          </button>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-5">
        <!-- Properties -->
        <div class="card p-5 space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <Home :size="13" /> Properties
          </div>
          <div v-if="local.properties?.length" class="space-y-2">
            <router-link
              v-for="p in local.properties"
              :key="p.id"
              :to="`/properties/${p.id}`"
              class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <Home :size="13" class="text-gray-400" />
              {{ p.name }}
            </router-link>
          </div>
          <p v-else class="text-xs text-gray-400">No properties linked.</p>
        </div>

        <!-- Stats -->
        <div class="card p-5 space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <BarChart3 :size="13" /> Summary
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="text-center py-3 bg-gray-50 rounded-lg">
              <div class="text-xl font-bold text-navy">{{ local.properties?.length ?? 0 }}</div>
              <div class="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Properties</div>
            </div>
            <div class="text-center py-3 bg-gray-50 rounded-lg">
              <div class="text-xl font-bold text-navy">{{ local.bank_accounts?.length ?? 0 }}</div>
              <div class="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Bank Acc.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tab: Address ── -->
    <div v-else-if="activeTab === 'address'" class="max-w-2xl pt-6">
      <div class="card p-5 space-y-4">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Address (Domicilium)</div>
        <div>
          <label class="label">Search address</label>
          <AddressAutocomplete input-class="input" @select="onAddressSelect" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="label">Street</label>
            <input v-model="local.address.street" class="input" />
          </div>
          <div>
            <label class="label">City</label>
            <input v-model="local.address.city" class="input" />
          </div>
          <div>
            <label class="label">Province</label>
            <input v-model="local.address.province" class="input" />
          </div>
          <div>
            <label class="label">Postal code</label>
            <input v-model="local.address.postal_code" class="input" />
          </div>
        </div>
        <button class="btn-primary text-sm" :disabled="saving" @click="saveLandlord">
          <Loader2 v-if="saving" :size="14" class="animate-spin" />
          Save Address
        </button>
      </div>
    </div>

    <!-- ── Tab: Bank Accounts ── -->
    <div v-else-if="activeTab === 'bank'" class="max-w-3xl space-y-4 pt-6">
      <div class="flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Bank Accounts</div>
        <button class="btn-ghost text-sm flex items-center gap-1.5" @click="addBankAccount">
          <Plus :size="14" /> Add account
        </button>
      </div>

      <div v-if="!local.bank_accounts?.length" class="card p-8 text-center">
        <Landmark :size="32" class="mx-auto text-gray-300 mb-3" />
        <p class="text-sm text-gray-400">No bank accounts added yet.</p>
        <button class="btn-primary btn-sm mt-3" @click="addBankAccount">
          <Plus :size="14" /> Add bank account
        </button>
      </div>

      <div v-for="(ba, idx) in local.bank_accounts" :key="ba.id ?? `new-${idx}`" class="card p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Landmark :size="15" class="text-gray-400" />
            <span class="font-medium text-sm text-gray-900">{{ ba.bank_name || 'New Account' }}</span>
            <span v-if="ba.is_default" class="badge-navy text-[10px]">Default</span>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Bank</label>
            <input v-model="ba.bank_name" class="input" />
          </div>
          <div>
            <label class="label">Account holder</label>
            <input v-model="ba.account_holder" class="input" />
          </div>
          <div>
            <label class="label">Account no.</label>
            <input v-model="ba.account_number" class="input font-mono" />
          </div>
          <div>
            <label class="label">Branch code</label>
            <input v-model="ba.branch_code" class="input font-mono" />
          </div>
          <div>
            <label class="label">Type</label>
            <input v-model="ba.account_type" class="input" placeholder="e.g. Cheque, Savings" />
          </div>
          <div>
            <label class="label">Label</label>
            <input v-model="ba.label" class="input" placeholder="e.g. Main rental account" />
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <label class="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
            <input type="checkbox" v-model="ba.is_default" class="rounded text-navy" />
            Default account
          </label>
          <div class="flex items-center gap-2">
            <button class="btn-primary text-xs" @click="saveBankAccount(ba)" :disabled="saving">
              <Loader2 v-if="saving" :size="12" class="animate-spin" />
              {{ ba.id ? 'Update' : 'Save Account' }}
            </button>
            <button v-if="ba.id" class="text-xs text-red-500 hover:underline" @click="deleteBankAccount(ba)">Remove</button>
            <button v-else class="text-xs text-gray-400 hover:underline" @click="local.bank_accounts.splice(idx, 1)">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tab: Properties ── -->
    <div v-else-if="activeTab === 'properties'" class="max-w-3xl space-y-4 pt-6">
      <div class="flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Linked Properties</div>
        <div class="flex items-center gap-2">
          <button class="btn-ghost text-sm flex items-center gap-1.5" @click="showLinkModal = true">
            <Plus :size="14" /> Link property
          </button>
          <button class="btn-ghost text-sm flex items-center gap-1.5" @click="$router.push('/properties')">
            <Plus :size="14" /> Add new property
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!local.properties?.length" class="card p-8 text-center">
        <Home :size="32" class="mx-auto text-gray-300 mb-3" />
        <p class="text-sm text-gray-400">No properties linked to this owner yet.</p>
        <button class="btn-primary btn-sm mt-3" @click="showLinkModal = true">
          <Plus :size="14" /> Link a property
        </button>
      </div>

      <!-- Property rows -->
      <div
        v-for="p in local.properties"
        :key="p.id"
        class="card p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
        @click="$router.push(`/properties/${p.id}`)"
      >
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-navy/5 flex items-center justify-center">
            <Home :size="16" class="text-navy" />
          </div>
          <div>
            <div class="font-medium text-sm text-gray-900">{{ p.name }}</div>
            <div class="text-xs text-gray-400">Property</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="text-xs text-red-500 hover:underline"
            @click.stop="unlinkProperty(p.ownership_id)"
          >
            Unlink
          </button>
          <ChevronRight :size="16" class="text-gray-300" />
        </div>
      </div>

      <!-- Link property modal -->
      <BaseModal :open="showLinkModal" title="Link Property" @close="showLinkModal = false; propertySearch = ''">
        <div class="space-y-3">
          <div>
            <label class="label">Search properties</label>
            <input v-model="propertySearch" class="input" placeholder="Type to filter…" />
          </div>
          <div class="max-h-60 overflow-y-auto space-y-1.5 border border-gray-100 rounded-xl p-2">
            <div v-if="!filteredUnlinkedProperties.length" class="text-xs text-gray-400 text-center py-3">
              No available properties found.
            </div>
            <button
              v-for="p in filteredUnlinkedProperties"
              :key="p.id"
              class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-colors text-sm"
              :class="selectedPropertyId === p.id ? 'bg-navy text-white' : 'hover:bg-gray-50 text-gray-700'"
              @click="selectedPropertyId = p.id"
            >
              <Home :size="14" :class="selectedPropertyId === p.id ? 'text-white' : 'text-gray-400'" />
              {{ p.name }}
            </button>
          </div>
          <div class="flex justify-end gap-2 pt-1">
            <button class="btn-ghost text-sm" @click="showLinkModal = false; selectedPropertyId = null; propertySearch = ''">Cancel</button>
            <button class="btn-primary text-sm" :disabled="!selectedPropertyId || linkingProperty" @click="linkProperty">
              <Loader2 v-if="linkingProperty" :size="14" class="animate-spin" />
              Link Property
            </button>
          </div>
        </div>
      </BaseModal>
    </div>

    <!-- ── Tab: FICA / CIPC Classification ── -->
    <div v-else-if="activeTab === 'classification'" class="space-y-5 pt-6">

      <!-- Document upload area -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <FileUp :size="13" /> Owner Documents
          </div>
          <span class="text-xs text-gray-400">{{ ficaDocs.length }} file{{ ficaDocs.length !== 1 ? 's' : '' }} uploaded</span>
        </div>

        <!-- Drag & drop zone -->
        <label
          class="flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors mb-3"
          :class="uploadingDocs ? 'border-navy/30 bg-navy/5' : 'border-gray-200 hover:border-navy/40 hover:bg-gray-50'"
        >
          <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
            <Upload :size="18" class="text-gray-400" />
          </div>
          <div class="text-center">
            <span class="text-sm font-medium text-gray-700">Drop documents here or click to browse</span>
            <p class="text-xs text-gray-400 mt-0.5">PDF, JPG, PNG, DOCX — multiple files supported</p>
          </div>
          <Loader2 v-if="uploadingDocs" :size="16" class="animate-spin text-navy" />
          <input type="file" class="hidden" multiple accept=".pdf,.jpg,.jpeg,.png,.docx" @change="uploadFicaDocs" />
        </label>

        <!-- Uploaded files list -->
        <div v-if="ficaDocs.length" class="space-y-1.5">
          <div
            v-for="doc in ficaDocs" :key="doc.id"
            class="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-50 border border-gray-100 group"
          >
            <FileText :size="14" class="text-gray-400 flex-shrink-0" />
            <span class="text-sm text-gray-700 flex-1 truncate">{{ doc.filename }}</span>
            <a :href="doc.file_url" target="_blank" class="p-1 rounded text-gray-300 hover:text-navy transition-colors" aria-label="View file">
              <Eye :size="13" />
            </a>
            <button class="p-1 rounded text-gray-300 hover:text-danger-500 transition-colors" aria-label="Delete file" @click="deleteFicaDoc(doc)">
              <X :size="13" />
            </button>
          </div>
        </div>
        <p v-else class="text-xs text-gray-400 text-center py-1">No documents uploaded yet.</p>
      </div>

      <!-- Classifier instructions + JSON upload -->
      <div class="card p-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-3">
          <ShieldCheck :size="13" /> AI Classification
        </div>
        <div class="flex items-start gap-3">
          <div class="flex-1">
            <p v-if="!local.classification_data" class="text-xs text-gray-500">
              Upload documents above, then click <strong>Run AI Classifier</strong>. Claude Sonnet will read every document, classify FICA vs CIPC, extract all fields, and auto-fill the registration number and other details.
            </p>
            <p v-else class="text-xs text-gray-500">Classification complete. Re-run to update after adding more documents.</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button
              class="btn-primary btn-sm flex items-center gap-1.5"
              :disabled="classifying || !ficaDocs.length"
              @click="runClassifier"
            >
              <Loader2 v-if="classifying" :size="13" class="animate-spin" />
              <Sparkles v-else :size="13" />
              {{ classifying ? 'Classifying…' : 'Run AI Classifier' }}
            </button>
            <label class="btn-ghost btn-sm cursor-pointer flex items-center gap-1.5">
              <Upload :size="13" /> JSON
              <input type="file" accept=".json" class="hidden" @change="uploadClassification" />
            </label>
          </div>
        </div>
        <p v-if="classifyError" class="text-xs text-danger-600 mt-2 flex items-center gap-1">
          <AlertTriangle :size="12" /> {{ classifyError }}
        </p>
      </div>

      <!-- No classification data — stop here -->
      <div v-if="!local.classification_data" class="text-center py-4 text-xs text-gray-300">Classification results will appear here once JSON is uploaded.</div>

      <!-- Classification results -->
      <template v-if="local.classification_data">
        <!-- Header -->
        <div>
          <h3 class="text-sm font-semibold text-gray-900">{{ local.classification_data.entity_type }} — {{ local.classification_data.entity_subtype || local.classification_data.entity_type }}</h3>
          <p class="text-xs text-gray-400 mt-0.5">
            Classified {{ local.classification_data.classified_at ? new Date(local.classification_data.classified_at).toLocaleDateString('en-ZA') : 'unknown date' }}
            <span v-if="local.classification_data.owned_by_trust" class="ml-2 badge-purple text-[10px]">Trust-owned</span>
          </p>
        </div>

        <!-- FICA card -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
              <ShieldCheck :size="13" /> FICA Status
            </div>
            <span :class="statusBadge(local.classification_data.fica?.status)">{{ local.classification_data.fica?.status ?? '—' }}</span>
          </div>

          <!-- Found docs -->
          <div v-if="local.classification_data.fica?.documents?.length" class="space-y-2 mb-3">
            <div v-for="doc in local.classification_data.fica.documents" :key="doc.filename"
                 class="flex items-start gap-2 text-sm text-gray-700">
              <CheckCircle2 :size="15" class="text-success-600 flex-shrink-0 mt-0.5" />
              <div>
                <span class="font-medium">{{ doc.type }}</span>
                <span class="text-gray-400 ml-1">— {{ doc.filename }}</span>
                <div v-if="doc.extracted?.full_name" class="text-xs text-gray-500">{{ doc.extracted.full_name }}</div>
              </div>
            </div>
          </div>

          <!-- Missing docs -->
          <div v-if="local.classification_data.fica?.missing?.length" class="space-y-1.5 mb-3">
            <div v-for="m in local.classification_data.fica.missing" :key="m"
                 class="flex items-center gap-2 text-sm text-danger-600">
              <XCircle :size="15" class="flex-shrink-0" />
              <span>{{ m }}</span>
            </div>
          </div>

          <!-- Flags -->
          <div v-if="local.classification_data.fica?.flags?.length" class="space-y-1.5">
            <div v-for="f in local.classification_data.fica.flags" :key="f"
                 class="flex items-start gap-2 text-xs text-warning-600 bg-warning-50 rounded-lg px-3 py-2">
              <AlertTriangle :size="13" class="flex-shrink-0 mt-0.5" />
              <span>{{ f }}</span>
            </div>
          </div>
        </div>

        <!-- CIPC card -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
              <Building2 :size="13" /> CIPC Status
            </div>
            <span :class="statusBadge(local.classification_data.cipc?.status)">{{ local.classification_data.cipc?.status ?? '—' }}</span>
          </div>

          <div v-if="local.classification_data.cipc?.documents?.length" class="space-y-2 mb-3">
            <div v-for="doc in local.classification_data.cipc.documents" :key="doc.filename"
                 class="flex items-start gap-2 text-sm text-gray-700">
              <CheckCircle2 :size="15" class="text-success-600 flex-shrink-0 mt-0.5" />
              <div>
                <span class="font-medium">{{ doc.type }}</span>
                <span class="text-gray-400 ml-1">— {{ doc.filename }}</span>
                <div v-if="doc.extracted?.registration_number" class="text-xs text-gray-500 font-mono">{{ doc.extracted.registration_number }}</div>
              </div>
            </div>
          </div>

          <div v-if="local.classification_data.cipc?.missing?.length" class="space-y-1.5 mb-3">
            <div v-for="m in local.classification_data.cipc.missing" :key="m"
                 class="flex items-center gap-2 text-sm text-danger-600">
              <XCircle :size="15" class="flex-shrink-0" />
              <span>{{ m }}</span>
            </div>
          </div>

          <div v-if="local.classification_data.cipc?.flags?.length" class="space-y-1.5">
            <div v-for="f in local.classification_data.cipc.flags" :key="f"
                 class="flex items-start gap-2 text-xs text-warning-600 bg-warning-50 rounded-lg px-3 py-2">
              <AlertTriangle :size="13" class="flex-shrink-0 mt-0.5" />
              <span>{{ f }}</span>
            </div>
          </div>
        </div>

        <!-- Trust entity block (if company owned by trust) -->
        <div v-if="local.classification_data.owned_by_trust && local.classification_data.trust_entity" class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-4">
            <Shield :size="13" /> Trust Entity — {{ local.classification_data.trust_entity.trust_name }}
          </div>
          <div class="grid grid-cols-2 gap-3 text-sm mb-4">
            <div>
              <span class="text-gray-400 text-xs">Trust number</span>
              <div class="font-mono text-gray-800">{{ local.classification_data.trust_entity.trust_number || '—' }}</div>
            </div>
            <div>
              <span class="text-gray-400 text-xs">URN</span>
              <div class="font-mono text-gray-800">{{ local.classification_data.trust_entity.urn || '—' }}</div>
            </div>
          </div>
          <div class="flex items-center gap-3 flex-wrap">
            <span :class="statusBadge(local.classification_data.trust_entity.fica?.status)" class="text-xs">FICA: {{ local.classification_data.trust_entity.fica?.status ?? '—' }}</span>
            <span :class="statusBadge(local.classification_data.trust_entity.cipc?.status)" class="text-xs">CIPC: {{ local.classification_data.trust_entity.cipc?.status ?? '—' }}</span>
          </div>
        </div>

        <!-- Persons graph -->
        <div v-if="local.classification_data.persons_graph?.length" class="card p-5">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-4">
            <Users :size="13" /> Persons Graph
          </div>
          <div class="space-y-4">
            <div v-for="person in local.classification_data.persons_graph" :key="person.id_number"
                 class="border border-gray-200 rounded-xl p-4">
              <div class="flex items-start justify-between gap-3 mb-2">
                <div>
                  <div class="font-medium text-sm text-gray-900">{{ person.full_name }}</div>
                  <div class="text-xs font-mono text-gray-400">{{ person.id_number }}</div>
                </div>
                <div class="flex items-center gap-1.5 flex-wrap justify-end">
                  <span v-if="person.joint_flag" class="badge-amber text-[10px]">Joint</span>
                  <span v-if="person.fica_documents_found?.length" class="badge-green text-[10px]">ID found</span>
                  <span v-else class="badge-red text-[10px]">ID missing</span>
                </div>
              </div>
              <!-- Roles -->
              <div class="flex flex-wrap gap-1.5 mb-2">
                <span v-for="role in person.roles" :key="`${role.entity}-${role.role}`"
                      class="text-xs px-2 py-0.5 bg-navy/5 text-navy rounded-full">
                  {{ role.role }} — {{ role.entity }}
                </span>
              </div>
              <!-- System records -->
              <div v-if="person.system_records?.length" class="mt-2 p-2.5 bg-warning-50 rounded-lg">
                <p class="text-xs font-medium text-warning-700 flex items-center gap-1">
                  <AlertTriangle :size="11" /> {{ person.system_note }}
                </p>
              </div>
              <!-- FICA reuse note -->
              <p v-if="person.fica_reuse_note" class="text-xs text-gray-400 mt-1.5 italic">{{ person.fica_reuse_note }}</p>
              <!-- Joint description -->
              <p v-if="person.joint_description" class="text-xs text-warning-700 mt-1.5">⚠ {{ person.joint_description }}</p>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ── Tab: Registration Documents ── -->
    <div v-else-if="activeTab === 'document'" class="max-w-3xl space-y-4 pt-6">

      <!-- Upload area — multiple files -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <FileUp :size="13" /> Registration Documents
          </div>
          <span class="text-xs text-gray-400">{{ ficaDocs.length }} file{{ ficaDocs.length !== 1 ? 's' : '' }}</span>
        </div>

        <p class="text-sm text-gray-500 mb-4">
          Upload CIPC certificates, trust deeds, ID documents, or any registration paperwork for this
          {{ entityLabel }}.
        </p>

        <!-- Drag & drop — multi-file -->
        <label
          class="flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors mb-3"
          :class="uploadingDocs ? 'border-navy/30 bg-navy/5' : 'border-gray-200 hover:border-navy/40 hover:bg-gray-50'"
        >
          <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
            <Upload :size="18" class="text-gray-400" />
          </div>
          <div class="text-center">
            <span class="text-sm font-medium text-gray-700">Drop documents here or click to browse</span>
            <p class="text-xs text-gray-400 mt-0.5">PDF, JPG, PNG, DOCX — multiple files supported</p>
          </div>
          <Loader2 v-if="uploadingDocs" :size="16" class="animate-spin text-navy" />
          <input type="file" class="hidden" multiple accept=".pdf,.jpg,.jpeg,.png,.docx" @change="uploadFicaDocs" />
        </label>

        <!-- File list -->
        <div v-if="ficaDocs.length" class="space-y-1.5">
          <div
            v-for="doc in ficaDocs" :key="doc.id"
            class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-gray-50 border border-gray-100 group"
          >
            <FileText :size="14" class="text-gray-400 flex-shrink-0" />
            <span class="text-sm text-gray-700 flex-1 truncate">{{ doc.filename }}</span>
            <span class="text-[10px] text-gray-400">{{ formatDate(doc.uploaded_at) }}</span>
            <a :href="doc.file_url" target="_blank" class="p-1 rounded text-gray-300 hover:text-navy transition-colors" title="View">
              <Eye :size="13" />
            </a>
            <a :href="doc.file_url" download class="p-1 rounded text-gray-300 hover:text-navy transition-colors" title="Download">
              <Download :size="13" />
            </a>
            <button class="p-1 rounded text-gray-300 hover:text-danger-500 transition-colors" title="Remove" @click="deleteFicaDoc(doc)">
              <X :size="13" />
            </button>
          </div>
        </div>
        <p v-else class="text-xs text-gray-400 text-center py-1">No documents uploaded yet.</p>
      </div>

      <!-- Expected documents reference -->
      <div class="card p-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-3">
          <FileText :size="13" /> Expected Documents
        </div>
        <div class="grid grid-cols-2 gap-4">
          <!-- FICA column -->
          <div>
            <div class="text-xs font-semibold text-gray-600 mb-2">FICA (KYC)</div>
            <ul class="space-y-1.5 text-xs text-gray-600">
              <li class="flex items-start gap-1.5">
                <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                Certified ID copies of all directors / members / trustees
              </li>
              <li class="flex items-start gap-1.5">
                <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                Proof of Address (utility bill, municipal, bank statement — &lt;3 months old)
              </li>
              <li class="flex items-start gap-1.5">
                <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                Bank Confirmation Letter
              </li>
              <li class="flex items-start gap-1.5">
                <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                SARS Tax Clearance Certificate
              </li>
              <li class="flex items-start gap-1.5">
                <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                VAT Registration Certificate (if VAT registered)
              </li>
            </ul>
          </div>
          <!-- CIPC / Entity column -->
          <div>
            <div class="text-xs font-semibold text-gray-600 mb-2">CIPC / Entity Registration</div>
            <ul class="space-y-1.5 text-xs text-gray-600">
              <!-- Company / Pty Ltd -->
              <template v-if="local.landlord_type === 'company'">
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR14.3 — Notice of Incorporation
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR15.1A/B — Memorandum of Incorporation (MOI)
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR21.1 — Registration Certificate
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR39 — Registered Office / Director Register
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR30.1 — Annual Return
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Board Resolution (authorising the transaction)
                </li>
              </template>
              <!-- CC -->
              <template v-else-if="local.landlord_type === 'cc'">
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CK1 — Founding Statement
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CK2 / CK2A — Amended Founding Statement
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  CoR30.1 — Annual Return
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Member interests schedule (% ownership)
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Members' Resolution (authorising the transaction)
                </li>
              </template>
              <!-- Trust -->
              <template v-else-if="local.landlord_type === 'trust'">
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Trust Deed / Deed of Trust
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  J101 — Letters of Authority (Master of the High Court)
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  J401 — Appointment of Trustees
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Trustee Resolution (authorising the transaction)
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Beneficial Ownership Register (required since 1 Apr 2023)
                </li>
              </template>
              <!-- Partnership -->
              <template v-else-if="local.landlord_type === 'partnership'">
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Partnership Agreement (signed by all partners)
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  Letter from senior partner confirming partnership
                </li>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  IDs of all partners (25%+ profit share)
                </li>
              </template>
              <!-- Individual -->
              <template v-else>
                <li class="flex items-start gap-1.5">
                  <span class="w-1 h-1 rounded-full bg-navy mt-1.5 flex-shrink-0" />
                  SA Identity Document (Smart ID / Green ID / Passport)
                </li>
              </template>
              <!-- Trust-owned add-on -->
              <template v-if="local.owned_by_trust && (local.landlord_type === 'company' || local.landlord_type === 'cc')">
                <li class="flex items-start gap-1.5 text-purple-700 mt-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1 flex-shrink-0" />
                  <strong>Owning Trust:</strong>
                </li>
                <li class="flex items-start gap-1.5 text-purple-700">
                  <span class="w-1 h-1 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  Trust Deed (owning trust)
                </li>
                <li class="flex items-start gap-1.5 text-purple-700">
                  <span class="w-1 h-1 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  J101 — Letters of Authority (owning trust)
                </li>
                <li class="flex items-start gap-1.5 text-purple-700">
                  <span class="w-1 h-1 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
                  Certified IDs of all trustees
                </li>
              </template>
            </ul>
          </div>
        </div>
      </div>

      <!-- AI Classify section -->
      <div class="card p-5">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-1">
              <Sparkles :size="13" /> AI Classification
            </div>
            <p class="text-xs text-gray-500">
              Reads all uploaded documents with AI — extracts entity type, registration number, directors, and auto-fills the owner record.
            </p>
          </div>
          <button
            class="btn-primary btn-sm flex items-center gap-1.5 flex-shrink-0 ml-4"
            :disabled="classifyingReg || !ficaDocs.length"
            @click="runRegClassifier"
          >
            <Loader2 v-if="classifyingReg" :size="13" class="animate-spin" />
            <Sparkles v-else :size="13" />
            {{ classifyingReg ? 'Classifying…' : 'Classify Documents' }}
          </button>
        </div>
        <p v-if="classifyRegError" class="text-xs text-danger-600 mt-2 flex items-center gap-1">
          <AlertTriangle :size="12" /> {{ classifyRegError }}
        </p>

        <!-- Extracted data summary (after classification) -->
        <div v-if="regClassification" class="mt-4 border-t border-gray-100 pt-4 space-y-3">
          <div class="flex items-center gap-2 mb-2">
            <span class="badge-green text-xs">Classified</span>
            <span class="text-xs text-gray-400">{{ regClassification.entity_type }} {{ regClassification.entity_subtype ? '— ' + regClassification.entity_subtype : '' }}</span>
          </div>

          <!-- Extracted fields -->
          <div v-if="regClassification.extracted_data" class="grid grid-cols-2 gap-3 text-sm">
            <div v-if="regClassification.extracted_data.company_name">
              <span class="text-gray-400 text-xs">Company name</span>
              <div class="text-gray-800 font-medium">{{ regClassification.extracted_data.company_name }}</div>
            </div>
            <div v-if="regClassification.extracted_data.registration_number">
              <span class="text-gray-400 text-xs">Registration no.</span>
              <div class="text-gray-800 font-mono">{{ regClassification.extracted_data.registration_number }}</div>
            </div>
            <div v-if="regClassification.extracted_data.vat_number">
              <span class="text-gray-400 text-xs">VAT number</span>
              <div class="text-gray-800 font-mono">{{ regClassification.extracted_data.vat_number }}</div>
            </div>
            <div v-if="regClassification.extracted_data.tax_number">
              <span class="text-gray-400 text-xs">Tax number</span>
              <div class="text-gray-800 font-mono">{{ regClassification.extracted_data.tax_number }}</div>
            </div>
            <div v-if="regClassification.extracted_data.address" class="col-span-2">
              <span class="text-gray-400 text-xs">Address</span>
              <div class="text-gray-800">{{ regClassification.extracted_data.address }}</div>
            </div>
          </div>

          <!-- Directors / Members -->
          <div v-if="regClassification.extracted_data?.directors?.length">
            <div class="text-xs text-gray-400 mb-1.5">Directors / Members</div>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="d in regClassification.extracted_data.directors" :key="d.id_number || d.name || d"
                    class="text-xs px-2 py-0.5 bg-navy/5 text-navy rounded-full">
                {{ typeof d === 'string' ? d : (d.name || d.full_name) }}
                <span v-if="d.id_number" class="text-gray-400 ml-1 font-mono">{{ d.id_number }}</span>
              </span>
            </div>
          </div>

          <!-- CIPC docs found/missing -->
          <div v-if="regClassification.cipc" class="flex items-center gap-3 flex-wrap">
            <span :class="statusBadge(regClassification.cipc.status)">CIPC: {{ regClassification.cipc.status }}</span>
            <span v-if="regClassification.cipc.missing?.length" class="text-xs text-danger-600">
              Missing: {{ regClassification.cipc.missing.join(', ') }}
            </span>
          </div>

          <!-- Flags -->
          <div v-if="regClassification.cipc?.flags?.length" class="space-y-1">
            <div v-for="f in regClassification.cipc.flags" :key="f"
                 class="flex items-start gap-2 text-xs text-warning-600 bg-warning-50 rounded-lg px-3 py-2">
              <AlertTriangle :size="12" class="flex-shrink-0 mt-0.5" />
              <span>{{ f }}</span>
            </div>
          </div>

          <!-- Auto-filled fields -->
          <div v-if="regPatchedFields.length" class="pt-2 border-t border-gray-100">
            <p class="text-xs text-success-600 flex items-center gap-1">
              <CheckCircle2 :size="12" /> Auto-filled: {{ regPatchedFields.join(', ') }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm: delete landlord -->
    <ConfirmDialog
      :open="confirmDeleteOpen"
      title="Delete owner?"
      :description="`Delete owner &quot;${local.name || ''}&quot;? This cannot be undone.`"
      confirm-label="Delete"
      :loading="deletingLandlord"
      @confirm="doDeleteLandlord"
      @cancel="confirmDeleteOpen = false"
    />

    <!-- Confirm: unlink property -->
    <ConfirmDialog
      :open="confirmUnlinkOpen"
      title="Unlink property?"
      description="Remove this property from the owner? This cannot be undone."
      confirm-label="Unlink"
      :loading="unlinkingBusy"
      @confirm="doUnlinkProperty"
      @cancel="confirmUnlinkOpen = false; unlinkingOwnership = null"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle, ArrowLeft, BarChart3, Briefcase, Building2, CheckCircle2, ChevronRight,
  Download, Eye, FileText, FileUp, Home, Landmark, Loader2, MapPin,
  MoreHorizontal, Plus, Shield, ShieldCheck, Sparkles, Trash2, Upload, User, Users, X, XCircle,
} from 'lucide-vue-next'
import api from '../../api'
import AddressAutocomplete, { type AddressResult } from '../../components/AddressAutocomplete.vue'
import BaseModal from '../../components/BaseModal.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import { formatDate } from '../../utils/formatters'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const landlord = ref<any>(null)
const local = ref<any>({})
const loading = ref(false)
const saving = ref(false)
const menuOpen = ref(false)
const menuRef = ref<HTMLElement>()
const activeTab = ref('details')
const ficaDocs = ref<any[]>([])
const uploadingDocs = ref(false)
const classifying = ref(false)
const classifyError = ref('')

// Properties tab
const allProperties = ref<any[]>([])
const propertySearch = ref('')
const linkingProperty = ref(false)
const showLinkModal = ref(false)
const selectedPropertyId = ref<number | null>(null)

// CIPC tab classifier (shares document storage with FICA tab — backend has only
// one `landlord.documents` collection, so both tabs read/write the same list).
const classifyingReg = ref(false)
const classifyRegError = ref('')
const regClassification = ref<any>(null)
const regPatchedFields = ref<string[]>([])

// Confirm-dialog state
const confirmDeleteOpen = ref(false)
const deletingLandlord = ref(false)
const confirmUnlinkOpen = ref(false)
const unlinkingOwnership = ref<number | null>(null)
const unlinkingBusy = ref(false)

const entityLabel = computed(() => {
  const t = local.value.landlord_type
  if (t === 'company') return 'company'
  if (t === 'trust') return 'trust'
  if (t === 'cc') return 'close corporation'
  if (t === 'partnership') return 'partnership'
  return 'individual'
})

const tabs = [
  { key: 'details', label: 'Details', icon: FileText },
  { key: 'address', label: 'Address', icon: MapPin },
  { key: 'bank', label: 'Bank Accounts', icon: Landmark },
  { key: 'properties', label: 'Properties', icon: Home },
  { key: 'document', label: 'CIPC', icon: FileUp },
  { key: 'classification', label: 'FICA', icon: ShieldCheck },
]

onMounted(() => initLandlord())

// Re-init when navigating between different landlords (KeepAlive reuses the instance).
// Only fire when we're actually on the landlord-detail route — otherwise navigating to
// /properties/:id would also trigger this watcher and try to load the property id as a landlord.
watch(() => route.params.id, (newId, oldId) => {
  if (route.name !== 'landlord-detail') return
  if (newId && newId !== oldId) initLandlord()
})

function initLandlord() {
  // Reset state so stale data from a previously viewed landlord never bleeds through
  landlord.value = null
  local.value = {}
  ficaDocs.value = []
  regClassification.value = null
  regPatchedFields.value = []
  classifyError.value = ''
  classifyRegError.value = ''
  activeTab.value = 'details'
  loadLandlord()
  loadFicaDocs()
  loadAllProperties()
}

async function loadLandlord() {
  loading.value = true
  try {
    const { data } = await api.get(`/properties/landlords/${route.params.id}/`)
    landlord.value = data
    local.value = {
      ...JSON.parse(JSON.stringify(data)),
      address: data.address && typeof data.address === 'object' ? { ...data.address } : {},
    }
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load owner'))
  } finally {
    loading.value = false
  }
}

function onAddressSelect(result: AddressResult) {
  if (!local.value.address) local.value.address = {}
  local.value.address.street = result.street || result.formatted
  local.value.address.city = result.city
  local.value.address.province = result.province
  local.value.address.postal_code = result.postal_code
}

async function saveLandlord() {
  saving.value = true
  try {
    const { bank_accounts, properties, property_count, created_at, updated_at, ...payload } = local.value
    await api.patch(`/properties/landlords/${local.value.id}/`, payload)
    await loadLandlord()
    toast.success('Owner updated')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save owner'))
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  menuOpen.value = false
  confirmDeleteOpen.value = true
}

async function doDeleteLandlord() {
  deletingLandlord.value = true
  try {
    await api.delete(`/properties/landlords/${local.value.id}/`)
    confirmDeleteOpen.value = false
    toast.success('Owner deleted')
    router.push('/landlords')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete owner'))
  } finally {
    deletingLandlord.value = false
  }
}

async function loadAllProperties() {
  try {
    const { data } = await api.get('/properties/')
    allProperties.value = data.results ?? data
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load properties'))
  }
}

const filteredUnlinkedProperties = computed(() => {
  const linkedIds = new Set((local.value.properties ?? []).map((p: any) => p.id))
  return allProperties.value.filter((p: any) => {
    if (linkedIds.has(p.id)) return false
    if (propertySearch.value) return p.name.toLowerCase().includes(propertySearch.value.toLowerCase())
    return true
  })
})

async function linkProperty() {
  if (!selectedPropertyId.value) return
  if (!local.value.name?.trim()) {
    toast.error('Owner name is required before linking a property.')
    return
  }
  linkingProperty.value = true
  try {
    await api.post('/properties/ownerships/', {
      property: selectedPropertyId.value,
      landlord: local.value.id,
      owner_name: local.value.name,
      owner_type: local.value.landlord_type === 'company' ? 'company' : local.value.landlord_type === 'trust' ? 'trust' : 'individual',
      is_current: true,
      start_date: new Date().toISOString().slice(0, 10),
    })
    showLinkModal.value = false
    selectedPropertyId.value = null
    propertySearch.value = ''
    await loadLandlord()
    toast.success('Property linked')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to link property'))
  } finally {
    linkingProperty.value = false
  }
}

function unlinkProperty(ownershipId: number) {
  unlinkingOwnership.value = ownershipId
  confirmUnlinkOpen.value = true
}

async function doUnlinkProperty() {
  if (unlinkingOwnership.value == null) return
  unlinkingBusy.value = true
  try {
    await api.delete(`/properties/ownerships/${unlinkingOwnership.value}/`)
    confirmUnlinkOpen.value = false
    unlinkingOwnership.value = null
    await loadLandlord()
    toast.success('Property unlinked')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to unlink property'))
  } finally {
    unlinkingBusy.value = false
  }
}

function addBankAccount() {
  if (!local.value.bank_accounts) local.value.bank_accounts = []
  local.value.bank_accounts.push({
    landlord: local.value.id,
    bank_name: '', branch_code: '', account_number: '',
    account_type: '', account_holder: '', label: '', is_default: false,
  })
}

async function saveBankAccount(ba: any) {
  saving.value = true
  try {
    if (ba.id) {
      await api.patch(`/properties/bank-accounts/${ba.id}/`, ba)
    } else {
      await api.post('/properties/bank-accounts/', { ...ba, landlord: local.value.id })
    }
    await loadLandlord()
    toast.success('Bank account saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save bank account'))
  } finally {
    saving.value = false
  }
}

async function deleteBankAccount(ba: any) {
  if (!ba.id) return
  try {
    await api.delete(`/properties/bank-accounts/${ba.id}/`)
    await loadLandlord()
    toast.success('Bank account removed')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete bank account'))
  }
}

async function loadFicaDocs() {
  try {
    const { data } = await api.get(`/properties/landlords/${route.params.id}/fica-documents/`)
    ficaDocs.value = data
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load documents'))
  }
}

async function uploadFicaDocs(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files?.length) return
  uploadingDocs.value = true
  try {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    await api.post(`/properties/landlords/${local.value.id}/fica-documents/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await loadFicaDocs()
    toast.success(files.length === 1 ? 'Document uploaded' : `${files.length} documents uploaded`)
  } catch (err) {
    toast.error(extractApiError(err, 'Upload failed'))
  } finally {
    uploadingDocs.value = false
    ;(e.target as HTMLInputElement).value = ''
  }
}

async function deleteFicaDoc(doc: any) {
  try {
    await api.delete(`/properties/landlords/${local.value.id}/fica-documents/${doc.id}/`)
    await loadFicaDocs()
    toast.success('Document removed')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete document'))
  }
}

async function runRegClassifier() {
  classifyingReg.value = true
  classifyRegError.value = ''
  regClassification.value = null
  regPatchedFields.value = []
  try {
    const { data } = await api.post(`/properties/landlords/${local.value.id}/classify/`)
    regClassification.value = data.classification
    regPatchedFields.value = data.patched_fields || []
    await loadLandlord()
  } catch (err: any) {
    classifyRegError.value = err?.response?.data?.detail || 'Classification failed.'
  } finally {
    classifyingReg.value = false
  }
}

async function runClassifier() {
  classifying.value = true
  classifyError.value = ''
  try {
    await api.post(`/properties/landlords/${local.value.id}/classify/`)
    await loadLandlord()
    await loadFicaDocs()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || 'Classification failed. Check that the API key is configured.'
    classifyError.value = detail
  } finally {
    classifying.value = false
  }
}

async function uploadClassification(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    await api.patch(`/properties/landlords/${local.value.id}/`, { classification_data: data })
    await loadLandlord()
    activeTab.value = 'classification'
    toast.success('Classification uploaded')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to parse or upload classification JSON.'))
  } finally {
    ;(e.target as HTMLInputElement).value = ''
  }
}

function statusBadge(status: string | undefined): string {
  if (status === 'complete') return 'badge-green'
  if (status === 'incomplete') return 'badge-red'
  if (status === 'needs_review') return 'badge-amber'
  return 'badge-gray'
}

// Close menu on outside click
function onClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false
  }
}
onMounted(() => document.addEventListener('click', onClickOutside))
</script>

<style scoped>
.menu-item {
  @apply w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-gray-700
         hover:bg-gray-50 transition-colors text-left;
}
</style>
