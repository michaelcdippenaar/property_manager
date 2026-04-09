import { useQuasar } from 'quasar'
import { computed } from 'vue'

export function usePlatform() {
  const $q = useQuasar()

  const isIos     = computed(() => $q.platform.is.ios || false)
  const isAndroid = computed(() => $q.platform.is.android || false)

  // Platform-appropriate route transitions
  const enterTransition = computed(() =>
    isIos.value ? 'slideInRight' : 'fadeIn',
  )
  const leaveTransition = computed(() =>
    isIos.value ? 'slideOutLeft' : 'fadeOut',
  )

  // Dialog positioning
  const dialogPosition = computed<'bottom' | 'standard'>(() =>
    isIos.value ? 'bottom' : 'standard',
  )

  // Back icon
  const backIcon = computed(() =>
    isIos.value ? 'chevron_left' : 'arrow_back',
  )

  // Tab bar CSS class
  const tabBarClass = computed(() =>
    isIos.value ? 'ios-tab-bar' : 'md-bottom-nav',
  )

  // Header CSS class
  const headerClass = computed(() =>
    isIos.value ? 'ios-header' : 'md-header',
  )

  return {
    isIos,
    isAndroid,
    enterTransition,
    leaveTransition,
    dialogPosition,
    backIcon,
    tabBarClass,
    headerClass,
  }
}
