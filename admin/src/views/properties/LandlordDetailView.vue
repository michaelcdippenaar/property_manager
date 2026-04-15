<template>
  <div class="space-y-0">

    <!-- ── Page header ── -->
    <PageHeader
      :title="landlord?.name ?? '…'"
      :subtitle="landlord?.email || 'No email'"
      :crumbs="[
        { label: 'Dashboard', to: '/' },
        { label: 'Owners', to: '/landlords' },
        { label: landlord?.name ?? '…' },
      ]"
      back
    >
      <template #actions>
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
            <button class="menu-item" @click="menuOpen = false; setTab('bank')">
              <Landmark :size="15" class="text-gray-400" /> Add bank account
            </button>
            <div class="my-1 border-t border-gray-100" />
            <button class="menu-item text-danger-500 hover:bg-danger-50" @click="confirmDelete">
              <Trash2 :size="15" /> Delete owner
            </button>
          </div>
        </Transition>
      </div>
      </template>
    </PageHeader>

    <!-- ── Tabs ── -->
    <div class="flex items-center gap-1 border-b border-gray-200 mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === tab.key
          ? 'border-navy text-navy'
          : 'border-transparent text-gray-400 hover:text-gray-600 hover:border-gray-300'"
        @click="setTab(tab.key)"
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
      <form @submit.prevent="saveLandlord" class="col-span-2 space-y-6">
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

          <div class="space-y-4">
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
          </div>
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
        </div>

        <!-- Address -->
        <div v-if="local.address" class="card p-5 space-y-4">
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
          <button type="submit" class="btn-primary text-sm" :disabled="saving">
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            Save Changes
          </button>
        </div>
      </form>

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

        <!-- Stats — each tile is clickable -->
        <div class="card p-5 space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <BarChart3 :size="13" /> Summary
          </div>
          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              class="text-center py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              @click="$router.push('/properties')"
              title="View all properties"
            >
              <div class="text-xl font-bold text-navy">{{ local.properties?.length ?? 0 }}</div>
              <div class="text-xs uppercase tracking-wide text-gray-400 font-medium">Properties</div>
            </button>
            <button
              type="button"
              class="text-center py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              @click="setTab('bank')"
              title="Manage bank accounts"
            >
              <div class="text-xl font-bold text-navy">{{ local.bank_accounts?.length ?? 0 }}</div>
              <div class="text-xs uppercase tracking-wide text-gray-400 font-medium">Bank Acc.</div>
            </button>
          </div>
        </div>

        <!-- Documents Outstanding indicator — click to jump to Documents tab -->
        <button
          type="button"
          class="card p-5 w-full text-left space-y-3 transition-colors"
          :class="docsOutstandingCount || unallocatedDocs.length
            ? 'hover:bg-danger-50/50 border-danger-200'
            : 'hover:bg-gray-50'"
          @click="setTab('documents')"
        >
          <div class="flex items-center justify-between">
            <div class="text-xs font-semibold uppercase tracking-wide flex items-center gap-1.5"
                 :class="docsOutstandingCount || unallocatedDocs.length ? 'text-danger-600' : 'text-success-600'">
              <AlertTriangle v-if="docsOutstandingCount || unallocatedDocs.length" :size="13" />
              <CheckCircle2 v-else :size="13" />
              Documents
            </div>
            <ChevronRight :size="14" class="text-gray-300" />
          </div>
          <div v-if="docsOutstandingCount || unallocatedDocs.length" class="grid grid-cols-2 gap-3">
            <div class="text-center py-2 bg-danger-50/60 rounded-lg">
              <div class="text-xl font-bold text-danger-600">{{ docsOutstandingCount }}</div>
              <div class="text-xs uppercase tracking-wide text-gray-500 font-medium">Missing</div>
            </div>
            <div class="text-center py-2 bg-gray-50 rounded-lg">
              <div class="text-xl font-bold" :class="unallocatedDocs.length ? 'text-accent-600' : 'text-gray-400'">
                {{ unallocatedDocs.length }}
              </div>
              <div class="text-xs uppercase tracking-wide text-gray-500 font-medium">Unclassified</div>
            </div>
          </div>
          <p v-else class="text-xs text-gray-500">All required documents on file.</p>
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
            <span v-if="ba.is_default" class="badge-navy text-xs">Default</span>
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
            <button v-if="ba.id" class="text-xs text-danger-500 hover:underline" @click="deleteBankAccount(ba)">Remove</button>
            <button v-else class="text-xs text-gray-400 hover:underline" @click="local.bank_accounts.splice(idx, 1)">Cancel</button>
          </div>
        </div>

        <!-- Confirmation letter — only shown for saved accounts -->
        <div v-if="ba.id" class="pt-2 border-t border-gray-100">
          <div class="text-xs font-medium text-gray-500 mb-1.5">Bank Confirmation Letter</div>
          <div v-if="ba.confirmation_letter_url" class="flex items-center gap-3">
            <a :href="ba.confirmation_letter_url" target="_blank"
               class="flex items-center gap-1.5 text-xs text-navy hover:underline">
              <FileText :size="13" /> View letter
            </a>
            <button class="text-xs text-danger-500 hover:underline" @click="removeConfirmationLetter(ba)">
              Remove
            </button>
          </div>
          <label v-else class="inline-flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer hover:text-gray-600">
            <Upload :size="13" />
            <span>Upload confirmation letter</span>
            <input type="file" class="sr-only" accept=".pdf,.jpg,.jpeg,.png"
                   @change="uploadConfirmationLetter(ba, $event)" />
          </label>
        </div>
      </div>
    </div>

    <!-- ── Tab: Documents (unified) ── -->
    <div v-else-if="activeTab === 'documents'" class="space-y-5 pt-6">

      <!-- Hidden input used by per-row "Upload" buttons on the Classified checklist -->
      <input
        ref="targetedFileInput"
        type="file"
        class="hidden"
        accept=".pdf,.jpg,.jpeg,.png,.docx"
        @change="uploadTargetedDoc"
      />

      <!-- Sub-tab bar: Classified vs Unclassified -->
      <div class="flex items-center gap-1 border-b border-gray-200">
        <button
          type="button"
          class="px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5"
          :class="docsSubTab === 'classified'
            ? 'border-accent-500 text-navy'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
          @click="docsSubTab = 'classified'"
        >
          <ShieldCheck :size="14" />
          Classified
          <span class="text-micro text-gray-400">({{ ficaDocs.length - unallocatedDocs.length }})</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5"
          :class="docsSubTab === 'unclassified'
            ? 'border-accent-500 text-navy'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
          @click="docsSubTab = 'unclassified'"
        >
          <FileUp :size="14" />
          Unclassified
          <span
            class="text-micro"
            :class="unallocatedDocs.length ? 'text-danger-600 font-semibold' : 'text-gray-400'"
          >({{ unallocatedDocs.length }})</span>
        </button>
      </div>

      <!-- ── Sub-tab: Unclassified — upload + raw file list ── -->
      <div v-if="docsSubTab === 'unclassified'" class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
            <FileUp :size="13" /> Unclassified documents
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="unallocatedDocs.length"
              type="button"
              class="btn-ghost btn-xs"
              :disabled="downloadingUnclassified"
              @click="downloadAllUnclassified"
            >
              <Loader2 v-if="downloadingUnclassified" :size="11" class="animate-spin" />
              <Download v-else :size="11" />
              {{ downloadingUnclassified ? 'Downloading…' : 'Download all' }}
            </button>
            <span class="text-xs text-gray-400">
              {{ unallocatedDocs.length }} of {{ ficaDocs.length }} file{{ ficaDocs.length !== 1 ? 's' : '' }}
            </span>
          </div>
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

        <!-- Unclassified files list — docs the classifier hasn't slotted into a category -->
        <div v-if="unallocatedDocs.length" class="space-y-1">
          <div
            v-for="doc in unallocatedDocs" :key="doc.id"
            class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-gray-50 border border-gray-100 group"
          >
            <FileText :size="13" class="text-gray-400 flex-shrink-0" />
            <span class="text-xs text-gray-700 flex-1 truncate">{{ doc.filename }}</span>
            <a :href="doc.file_url" target="_blank" class="p-0.5 rounded text-gray-300 hover:text-navy transition-colors" aria-label="View file">
              <Eye :size="12" />
            </a>
            <button class="p-0.5 rounded text-gray-300 hover:text-danger-500 transition-colors" aria-label="Delete file" @click="deleteFicaDoc(doc)">
              <X :size="12" />
            </button>
          </div>
        </div>
        <p v-else-if="ficaDocs.length" class="text-xs text-gray-400 text-center py-1">All uploads classified — switch to the Classified tab to review.</p>
        <p v-else class="text-xs text-gray-400 text-center py-1">No documents uploaded yet.</p>
      </div>

      <!-- ── Sub-tab: Classified — classification results + category cards ── -->
      <template v-if="docsSubTab === 'classified'">

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
            <span v-if="local.classification_data.owned_by_trust" class="ml-2 badge-purple text-xs">Trust-owned</span>
          </p>
        </div>

        <!-- Category cards: CIPC / Directors / Banking / FICA / Property -->
        <div
          v-for="catKey in (['cipc','directors','banking','fica','property'] as const)"
          :key="catKey"
          class="card p-4"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
              <component :is="_DOC_CATEGORY_META[catKey].icon" :size="13" />
              {{ _DOC_CATEGORY_META[catKey].label }}
            </div>
            <span class="text-xs text-gray-400">
              {{ expectedDocs[catKey].filter((e) => isExpectedSatisfied(e, docsGroupedByCategory[catKey])).length }}/{{ expectedDocs[catKey].length }}
              <span v-if="extrasInCategory(catKey).length" class="ml-1">· +{{ extrasInCategory(catKey).length }}</span>
            </span>
          </div>

          <!-- Expected checklist — label on left, filename chip on right -->
          <div v-if="expectedDocs[catKey].length" class="space-y-0.5">
            <template v-for="exp in expectedDocs[catKey]" :key="`${catKey}-${exp.key}-${exp.label}`">
              <div
                class="flex items-center gap-2 text-xs py-0.5"
                :class="isExpectedSatisfied(exp, docsGroupedByCategory[catKey]) ? 'text-gray-700' : 'text-danger-600'"
              >
                <CheckCircle2
                  v-if="isExpectedSatisfied(exp, docsGroupedByCategory[catKey])"
                  :size="13" class="text-success-600 flex-shrink-0"
                />
                <XCircle v-else :size="13" class="flex-shrink-0" />
                <span class="font-medium flex-1 min-w-0 truncate" :title="exp.label">{{ exp.label }}</span>
                <a
                  v-if="isExpectedSatisfied(exp, docsGroupedByCategory[catKey])"
                  :href="fileUrlForDoc(isExpectedSatisfied(exp, docsGroupedByCategory[catKey]))"
                  target="_blank"
                  class="inline-flex items-center gap-1 max-w-[55%] rounded-md bg-gray-100 hover:bg-gray-200 px-2 py-0.5 text-micro text-gray-600 no-underline transition-colors"
                  :title="isExpectedSatisfied(exp, docsGroupedByCategory[catKey])?.filename"
                >
                  <FileText :size="11" class="text-gray-400 flex-shrink-0" />
                  <span class="truncate">{{ isExpectedSatisfied(exp, docsGroupedByCategory[catKey])?.filename }}</span>
                </a>
                <button
                  v-else
                  type="button"
                  class="inline-flex items-center gap-1 rounded-md border border-danger-200 bg-danger-50 hover:bg-danger-100 px-2 py-0.5 text-micro text-danger-700 hover:text-danger-800 transition-colors flex-shrink-0"
                  :disabled="uploadingDocs || classifying"
                  :title="`Upload ${exp.label}`"
                  @click="pickFileForExpected(exp)"
                >
                  <Upload :size="11" />
                  <span>{{ uploadingDocs && pendingDocType === exp.key ? 'Uploading…' : 'Upload' }}</span>
                </button>
              </div>
            </template>
          </div>

          <!-- Extras — classified docs in this category beyond the expected list -->
          <div v-if="extrasInCategory(catKey).length" class="mt-2 pt-2 border-t border-gray-100 space-y-0.5">
            <div
              v-for="doc in extrasInCategory(catKey)"
              :key="`${catKey}-extra-${doc.filename}`"
              class="flex items-center gap-2 text-xs text-gray-700 py-0.5"
            >
              <FileText :size="12" class="text-gray-400 flex-shrink-0" />
              <span class="font-medium flex-1 min-w-0 truncate">{{ doc.rawType || 'Unclassified' }}</span>
              <a
                :href="fileUrlForDoc(doc)"
                target="_blank"
                class="inline-flex items-center gap-1 max-w-[55%] rounded-md bg-gray-100 hover:bg-gray-200 px-2 py-0.5 text-micro text-gray-600 no-underline transition-colors"
                :title="doc.filename"
              >
                <FileText :size="11" class="text-gray-400 flex-shrink-0" />
                <span class="truncate">{{ doc.filename }}</span>
              </a>
            </div>
          </div>

          <p
            v-if="!expectedDocs[catKey].length && !extrasInCategory(catKey).length"
            class="text-xs text-gray-400"
          >
            Nothing required for this entity type.
          </p>
        </div>

        <!-- Flags rolled up from both buckets -->
        <div
          v-if="(local.classification_data.fica?.flags?.length || local.classification_data.cipc?.flags?.length)"
          class="card p-5"
        >
          <div class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5 mb-3">
            <AlertTriangle :size="13" /> Flags &amp; notes
          </div>
          <div class="space-y-1.5">
            <div
              v-for="f in [...(local.classification_data.fica?.flags || []), ...(local.classification_data.cipc?.flags || [])]"
              :key="f"
              class="flex items-start gap-2 text-xs text-warning-700 bg-warning-50 rounded-lg px-3 py-2"
            >
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
                  <span v-if="person.joint_flag" class="badge-amber text-xs">Joint</span>
                  <span v-if="person.fica_documents_found?.length" class="badge-green text-xs">ID found</span>
                  <span v-else class="badge-red text-xs">ID missing</span>
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
      </template>
    </div>

    <!-- ── Tab: Onboarding Assistant (AI chat) ── -->
    <div v-else-if="activeTab === 'assistant'" class="max-w-3xl pt-6">
      <OwnerChatPanel
        v-if="landlord?.id"
        :landlord-id="landlord.id"
      />
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
      @cancel="confirmUnlinkOpen = false; unlinkingOwnership = null; unlinkingPropertyId = null"
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
import PageHeader from '../../components/PageHeader.vue'
import BaseModal from '../../components/BaseModal.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import { formatDate } from '../../utils/formatters'
import { useLandlordsStore } from '../../stores/landlords'
import { useOwnershipsStore } from '../../stores/ownerships'
import OwnerChatPanel from '../../components/landlord/OwnerChatPanel.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const landlordsStore = useLandlordsStore()
const ownershipsStore = useOwnershipsStore()

const landlord = ref<any>(null)
const local = ref<any>({})
const loading = ref(false)
const saving = ref(false)
const menuOpen = ref(false)
const menuRef = ref<HTMLElement>()
const VALID_TABS = ['details', 'bank', 'documents', 'assistant'] as const
// Back-compat redirect — old tab keys route to the merged "documents" tab,
// or (for the removed "properties" tab) back to Details.
const _LEGACY_TAB_REDIRECTS: Record<string, (typeof VALID_TABS)[number]> = {
  document: 'documents',
  classification: 'documents',
  properties: 'details',
}
type TabKey = typeof VALID_TABS[number]
function _resolveTab(raw: unknown): TabKey {
  const s = String(raw ?? '')
  if (_LEGACY_TAB_REDIRECTS[s]) return _LEGACY_TAB_REDIRECTS[s]
  return (VALID_TABS as readonly string[]).includes(s) ? (s as TabKey) : 'details'
}
const activeTab = ref<TabKey>(_resolveTab(route.query.tab))

function setTab(key: TabKey) {
  activeTab.value = key
  router.replace({ query: { ...route.query, tab: key } })
}

watch(() => route.query.tab, (t) => {
  activeTab.value = _resolveTab(t)
})
const ficaDocs = ref<any[]>([])
const uploadingDocs = ref(false)
const classifying = ref(false)
const classifyError = ref('')
// Sub-tab under Documents: "classified" shows the category cards +
// classification results; "unclassified" shows the raw upload + list of
// docs the classifier hasn't slotted yet. Default to whichever side has
// something to do: if there are unclassified uploads, land there.
const docsSubTab = ref<'classified' | 'unclassified'>('classified')
// When the user clicks "Upload" next to a specific expected doc, we record
// which slot they're filling so the file picker opens in targeted mode and
// the upload button shows the right spinner.
const pendingDocType = ref<string | null>(null)
const targetedFileInput = ref<HTMLInputElement | null>(null)

// Properties tab
const allProperties = ref<any[]>([])
const propertySearch = ref('')
const linkingProperty = ref(false)
const showLinkModal = ref(false)
const selectedPropertyId = ref<number | null>(null)

// Confirm-dialog state
const confirmDeleteOpen = ref(false)
const deletingLandlord = ref(false)
const confirmUnlinkOpen = ref(false)
const unlinkingOwnership = ref<number | null>(null)
const unlinkingPropertyId = ref<number | null>(null)
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
  { key: 'bank', label: 'Bank Accounts', icon: Landmark },
  { key: 'documents', label: 'Documents', icon: FileUp },
  { key: 'assistant', label: 'Assistant', icon: Sparkles },
]

// ── Document category taxonomy ────────────────────────────────────────
// Five buckets the user sees on the Documents tab. Each uploaded +
// classified document gets sorted into one; each category lists the
// docs *expected* for this entity type plus any extras we found.

type DocCategoryKey = 'cipc' | 'directors' | 'banking' | 'fica' | 'property'

const _DOC_CATEGORY_META: Record<DocCategoryKey, { label: string; icon: any; blurb: string }> = {
  cipc:      { label: 'CIPC / Entity',  icon: Building2,  blurb: 'Company / trust / CC registration & governance.' },
  directors: { label: 'Directors & IDs', icon: Users,     blurb: 'Identity documents for every signatory (director, trustee, member).' },
  banking:   { label: 'Banking',        icon: Landmark,   blurb: 'Bank confirmation letter on bank letterhead.' },
  fica:      { label: 'FICA / Tax',     icon: ShieldCheck, blurb: 'Proof of address, SARS tax certificate, VAT registration.' },
  property:  { label: 'Property',       icon: Home,       blurb: 'Title deed or proof of ownership.' },
}

// Client-side canonicalisation — mirror of backend gap_analysis._norm_type.
// Classifier types come through as human labels or snake_case; collapse
// them to the same canonical keys the backend uses.
const _DOC_TYPE_ALIASES: Record<string, string> = {
  cor15_1a: 'moi', cor15_1b: 'moi', cor15: 'moi',
  memorandum_of_incorporation: 'moi', moi_cor15_1a: 'moi',
  bank_confirmation_letter: 'bank_confirmation',
  bank_letter: 'bank_confirmation',
  bank_reference_letter: 'bank_confirmation',
  municipal_account: 'proof_of_address',
  municipal_bill: 'proof_of_address',
  utility_bill: 'proof_of_address',
  proof_of_residence: 'proof_of_address',
  bank_statement: 'proof_of_address',
  rates_bill: 'proof_of_address',
  sars_tax_certificate: 'tax_certificate',
  tax_clearance_certificate: 'tax_certificate',
  sars_notice_of_registration: 'tax_certificate',
  vat_registration_certificate: 'vat_certificate',
  vat_registration: 'vat_certificate',
  deed_of_transfer: 'title_deed',
  registration_certificate: 'cor14_3', cor_14_3: 'cor14_3',
  director_notice: 'cor39', cor_39: 'cor39',
  ck_1: 'ck1', founding_statement: 'ck1',
  deed_of_trust: 'trust_deed',
  letter_of_authority: 'letters_of_authority', loa: 'letters_of_authority',
  identity_document: 'sa_id', id_document: 'sa_id',
  id_book: 'sa_id', id_card: 'sa_id',
  smart_id: 'sa_id', green_id: 'sa_id', green_id_book: 'sa_id',
  driver_licence: 'drivers_licence', drivers_license: 'drivers_licence',
}

function normDocType(raw: string | undefined | null): string {
  if (!raw) return ''
  let s = String(raw).toLowerCase()
  for (const ch of ['.', '-', ' ', '/', '(', ')', ',']) s = s.split(ch).join('_')
  while (s.includes('__')) s = s.split('__').join('_')
  s = s.replace(/^_+|_+$/g, '')
  return _DOC_TYPE_ALIASES[s] || s
}

// Category mapping for a canonical doc type. Anything unknown lands in CIPC
// (safest default — agents are already used to seeing extras there).
const _CATEGORY_BY_TYPE: Record<string, DocCategoryKey> = {
  // CIPC / entity
  cor14_3: 'cipc', moi: 'cipc', cor39: 'cipc', cor21: 'cipc', cor123: 'cipc',
  cor30_1: 'cipc', cor40: 'cipc',
  ck1: 'cipc', ck2: 'cipc', ck2a: 'cipc',
  trust_deed: 'cipc', letters_of_authority: 'cipc',
  partnership_agreement: 'cipc', beneficial_ownership_register: 'cipc',
  disclosure_certificate_cipc: 'cipc', share_certificate: 'cipc',
  securities_register: 'cipc', disclosure_structure: 'cipc',
  resolution: 'cipc', board_resolution: 'cipc',
  // Directors / people
  sa_id: 'directors', passport: 'directors', drivers_licence: 'directors',
  // Banking
  bank_confirmation: 'banking',
  // FICA / tax
  proof_of_address: 'fica', tax_certificate: 'fica', vat_certificate: 'fica',
  // Property
  title_deed: 'property',
}

function categoryForType(raw: string | undefined | null): DocCategoryKey {
  return _CATEGORY_BY_TYPE[normDocType(raw)] || 'cipc'
}

// Identity-doc synonyms — any of these satisfies the "SA ID" requirement.
const _IDENTITY_SYNONYMS = new Set(['sa_id', 'passport', 'drivers_licence'])

interface ExpectedDoc {
  key: string
  label: string
  satisfiedBy?: string[]
  // Per-property title deeds are pre-resolved against PropertyDocument
  // records on the backend; when `preSatisfied` is set, the expected row
  // skips the classifier-docs lookup and trusts this flag directly.
  preSatisfied?: boolean
  propertyId?: number
}

function expectedDocsByCategory(entityType: string, ownedByTrust: boolean): Record<DocCategoryKey, ExpectedDoc[]> {
  const cipc: ExpectedDoc[] = []
  if (entityType === 'company') {
    cipc.push(
      { key: 'cor14_3', label: 'CoR14.3 — Notice of Incorporation' },
      { key: 'moi', label: 'CoR15.1A/B — Memorandum of Incorporation (MOI)' },
      { key: 'cor39', label: 'CoR39 — Directors' },
      { key: 'cor21', label: 'CoR21.1 — Registered Office' },
    )
  } else if (entityType === 'cc') {
    cipc.push({ key: 'ck1', label: 'CK1 — Founding Statement' })
  } else if (entityType === 'trust') {
    cipc.push(
      { key: 'trust_deed', label: 'Trust Deed' },
      { key: 'letters_of_authority', label: 'J101 — Letters of Authority' },
    )
  } else if (entityType === 'partnership') {
    cipc.push({ key: 'partnership_agreement', label: 'Partnership Agreement' })
  }
  if (ownedByTrust && (entityType === 'company' || entityType === 'cc')) {
    cipc.push(
      { key: 'trust_deed', label: 'Owning-trust: Trust Deed' },
      { key: 'letters_of_authority', label: 'Owning-trust: Letters of Authority' },
    )
  }

  const directors: ExpectedDoc[] = [
    { key: 'sa_id', label: 'ID for every signatory (SA ID, passport, or driver\'s licence)',
      satisfiedBy: ['sa_id', 'passport', 'drivers_licence'] },
  ]
  const banking: ExpectedDoc[] = [
    { key: 'bank_confirmation', label: 'Bank Confirmation Letter (on letterhead)' },
  ]
  const fica: ExpectedDoc[] = [
    { key: 'proof_of_address', label: 'Proof of Address (< 3 months old)' },
    { key: 'tax_certificate', label: 'SARS Tax Certificate / Notice of Registration' },
    { key: 'vat_certificate', label: 'VAT Registration Certificate (if VAT-registered)' },
  ]
  // Title deeds live on the property, not the landlord. The per-property
  // list is injected by the `expectedDocs` computed so that a landlord
  // with N properties shows N title-deed rows, one labelled with each
  // property's name.
  const property: ExpectedDoc[] = []

  return { cipc, directors, banking, fica, property }
}

// Each classified doc, normalised and enriched for the category cards.
interface CategorisedDoc {
  category: DocCategoryKey
  rawType: string
  canonicalType: string
  filename: string
  extracted: Record<string, any>
  bucket: 'fica' | 'cipc'
}

const categorisedDocs = computed<CategorisedDoc[]>(() => {
  const cd = (local.value as any)?.classification_data
  if (!cd) return []
  // Only count a classified doc as "on file" if the physical upload still
  // exists in LandlordDocument — the classifier output can reference files
  // that were later deleted, which would otherwise show as satisfied.
  const uploadedNames = new Set(ficaDocs.value.map((d: any) => d.filename))
  const out: CategorisedDoc[] = []
  for (const bucket of ['fica', 'cipc'] as const) {
    const docs = (cd[bucket]?.documents || []) as any[]
    for (const d of docs) {
      const filename = String(d?.filename || '')
      if (!filename || !uploadedNames.has(filename)) continue
      const rawType = String(d?.type || '')
      const canonical = normDocType(rawType)
      out.push({
        category: categoryForType(rawType),
        rawType,
        canonicalType: canonical,
        filename,
        extracted: (d?.extracted || {}) as any,
        bucket,
      })
    }
  }
  return out
})

const docsGroupedByCategory = computed(() => {
  const groups: Record<DocCategoryKey, CategorisedDoc[]> = {
    cipc: [], directors: [], banking: [], fica: [], property: [],
  }
  for (const d of categorisedDocs.value) groups[d.category].push(d)
  return groups
})

const expectedDocs = computed(() => {
  const base = expectedDocsByCategory(
    (local.value?.landlord_type || 'individual') as string,
    Boolean(local.value?.owned_by_trust),
  )
  // Inject one title-deed row per linked property. Each row's satisfaction
  // is pre-resolved from the backend (has_title_deed) rather than scanned
  // out of the classifier output — title deeds are PropertyDocuments.
  const properties: Array<{ id: number; name: string; has_title_deed?: boolean }> =
    (local.value?.properties || []) as any
  base.property = properties.map((p) => ({
    key: `title_deed_${p.id}`,
    label: `Title Deed — ${p.name}`,
    propertyId: p.id,
    preSatisfied: Boolean(p.has_title_deed),
  }))
  return base
})

function isExpectedSatisfied(exp: ExpectedDoc, found: CategorisedDoc[]): CategorisedDoc | null {
  // Per-property title deeds are pre-resolved via PropertyDocument. A sentinel
  // match-like object lets the existing "satisfied" UI branch render without
  // a classifier hit — the filename chip falls back to "On file".
  if (exp.preSatisfied) {
    return { category: 'property', rawType: 'title_deed', canonicalType: 'title_deed', filename: 'On file' } as CategorisedDoc
  }
  if (exp.propertyId) return null  // unsatisfied title-deed row
  const keys = new Set(exp.satisfiedBy?.length ? exp.satisfiedBy : [exp.key])
  // SA ID is satisfied by any identity synonym.
  if (exp.key === 'sa_id') for (const s of _IDENTITY_SYNONYMS) keys.add(s)
  const match = found.find((d) => keys.has(d.canonicalType))
  return match || null
}

function extrasInCategory(cat: DocCategoryKey): CategorisedDoc[] {
  const expectedKeys = new Set(expectedDocs.value[cat].flatMap((e) =>
    e.satisfiedBy?.length ? e.satisfiedBy : [e.key],
  ))
  if (cat === 'directors') for (const s of _IDENTITY_SYNONYMS) expectedKeys.add(s)
  return docsGroupedByCategory.value[cat].filter((d) => !expectedKeys.has(d.canonicalType))
}

// Files the classifier has already slotted into a category. Used to
// hide "allocated" uploads from the unallocated-docs list.
const allocatedFilenames = computed<Set<string>>(() => {
  const s = new Set<string>()
  for (const d of categorisedDocs.value) if (d.filename) s.add(d.filename)
  return s
})

const unallocatedDocs = computed(() =>
  ficaDocs.value.filter((d: any) => !allocatedFilenames.value.has(d.filename)),
)

// Number of required/expected docs still missing across all five categories.
// Drives the "Documents Outstanding" indicator in the Details sidebar so the
// user can see at a glance how close this landlord is to mandate-ready.
const docsOutstandingCount = computed(() => {
  const cats: DocCategoryKey[] = ['cipc', 'directors', 'banking', 'fica', 'property']
  let missing = 0
  for (const cat of cats) {
    for (const exp of expectedDocs.value[cat] || []) {
      if (!isExpectedSatisfied(exp, docsGroupedByCategory.value[cat] || [])) missing += 1
    }
  }
  return missing
})

const downloadingUnclassified = ref(false)

// Download every unclassified doc by fetching each as a blob and triggering an
// anchor click. Sequential with a small delay so the browser doesn't coalesce
// or silently drop concurrent downloads.
async function downloadAllUnclassified(): Promise<void> {
  if (!unallocatedDocs.value.length || downloadingUnclassified.value) return
  downloadingUnclassified.value = true
  try {
    for (const doc of unallocatedDocs.value) {
      const url = (doc as any).file_url
      if (!url) continue
      try {
        const res = await fetch(url, { credentials: 'omit' })
        if (!res.ok) continue
        const blob = await res.blob()
        const blobUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = blobUrl
        a.download = (doc as any).filename || 'document'
        document.body.appendChild(a)
        a.click()
        a.remove()
        // Let the browser commit the download before starting the next one.
        await new Promise((r) => setTimeout(r, 250))
        URL.revokeObjectURL(blobUrl)
      } catch {
        // Skip files that fail (CORS, 403, etc.) rather than aborting the batch.
      }
    }
  } finally {
    downloadingUnclassified.value = false
  }
}

// Match a categorised doc back to its LandlordDocument to resolve a file URL
// for the "click to view" chip in each category row.
function fileUrlForDoc(doc: CategorisedDoc | null | undefined): string {
  if (!doc?.filename) return '#'
  const match = ficaDocs.value.find((d: any) => d.filename === doc.filename)
  return match?.file_url || '#'
}

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
  classifyError.value = ''
  activeTab.value = _resolveTab(route.query.tab)
  loadLandlord()
  loadFicaDocs()
  loadAllProperties()
}

async function loadLandlord() {
  loading.value = true
  try {
    const data = await landlordsStore.fetchOne(Number(route.params.id), { force: true })
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
    await landlordsStore.update(local.value.id, local.value)
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
    await landlordsStore.remove(local.value.id)
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
    const { data } = await api.get('/properties/', { params: { unlinked: true } })
    allProperties.value = data.results ?? data
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load properties'))
  }
}

const filteredUnlinkedProperties = computed(() => {
  const term = propertySearch.value.trim().toLowerCase()
  if (!term) return allProperties.value
  return allProperties.value.filter((p: any) => p.name.toLowerCase().includes(term))
})

async function linkProperty() {
  if (!selectedPropertyId.value) return
  if (!local.value.name?.trim()) {
    toast.error('Owner name is required before linking a property.')
    return
  }
  linkingProperty.value = true
  try {
    await ownershipsStore.create({
      property: selectedPropertyId.value,
      landlord: local.value.id,
      owner_name: local.value.name,
      owner_type: local.value.landlord_type === 'company' ? 'company' : local.value.landlord_type === 'trust' ? 'trust' : 'individual',
      is_current: true,
      start_date: new Date().toISOString().slice(0, 10),
    } as any)
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

function unlinkProperty(ownershipId: number, propertyId: number) {
  unlinkingOwnership.value = ownershipId
  unlinkingPropertyId.value = propertyId
  confirmUnlinkOpen.value = true
}

async function doUnlinkProperty() {
  if (unlinkingOwnership.value == null || unlinkingPropertyId.value == null) return
  unlinkingBusy.value = true
  try {
    await ownershipsStore.remove(unlinkingOwnership.value, unlinkingPropertyId.value)
    confirmUnlinkOpen.value = false
    unlinkingOwnership.value = null
    unlinkingPropertyId.value = null
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
    const fresh = await landlordsStore.saveBankAccount(local.value.id, ba)
    landlord.value = fresh
    local.value = {
      ...JSON.parse(JSON.stringify(fresh)),
      address: fresh.address && typeof fresh.address === 'object' ? { ...fresh.address } : {},
    }
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
    const fresh = await landlordsStore.deleteBankAccount(local.value.id, ba.id)
    landlord.value = fresh
    local.value = {
      ...JSON.parse(JSON.stringify(fresh)),
      address: fresh.address && typeof fresh.address === 'object' ? { ...fresh.address } : {},
    }
    toast.success('Bank account removed')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete bank account'))
  }
}

async function uploadConfirmationLetter(ba: any, e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  try {
    const { data } = await api.post(
      `/properties/bank-accounts/${ba.id}/upload-confirmation/`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    Object.assign(ba, data)
    toast.success('Confirmation letter uploaded')
  } catch (err) {
    toast.error(extractApiError(err, 'Upload failed'))
  }
  ;(e.target as HTMLInputElement).value = ''
}

async function removeConfirmationLetter(ba: any) {
  try {
    await api.delete(`/properties/bank-accounts/${ba.id}/remove-confirmation/`)
    ba.confirmation_letter_url = null
    toast.success('Letter removed')
  } catch (err) {
    toast.error(extractApiError(err, 'Remove failed'))
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

function pickFileForExpected(exp: ExpectedDoc): void {
  pendingDocType.value = exp.key
  targetedFileInput.value?.click()
}

async function uploadTargetedDoc(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length) {
    pendingDocType.value = null
    return
  }
  uploadingDocs.value = true
  try {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    // Hint the classifier about the expected slot — backend may or may not
    // use it, but sending it is cheap and unambiguous for future per-doc
    // classification.
    if (pendingDocType.value) form.append('doc_type_hint', pendingDocType.value)
    await api.post(`/properties/landlords/${local.value.id}/fica-documents/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await loadFicaDocs()
    toast.success('Document uploaded — re-running classifier')
    // Auto-run the classifier so the newly-uploaded file gets slotted into
    // the correct category without the user having to click a second button.
    try {
      classifying.value = true
      await api.post(`/properties/landlords/${local.value.id}/classify/`)
      await loadLandlord()
      await loadFicaDocs()
    } finally {
      classifying.value = false
    }
  } catch (err) {
    toast.error(extractApiError(err, 'Upload failed'))
  } finally {
    uploadingDocs.value = false
    pendingDocType.value = null
    input.value = ''
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
