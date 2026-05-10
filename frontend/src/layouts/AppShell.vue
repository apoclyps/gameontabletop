<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col">
    <!-- Top nav -->
    <header class="sticky top-0 z-40 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <!-- Logo -->
        <router-link to="/dashboard" class="flex items-center gap-2 flex-shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="w-8 h-8" fill="none">
            <rect x="1" y="1" width="30" height="30" rx="6" fill="#0d9488"/>
            <circle cx="9" cy="10" r="2.5" fill="white"/>
            <circle cx="23" cy="10" r="2.5" fill="white"/>
            <circle cx="9" cy="22" r="2.5" fill="white"/>
            <circle cx="23" cy="22" r="2.5" fill="white"/>
            <circle cx="16" cy="16" r="2.5" fill="white"/>
          </svg>
          <span class="font-bold text-base text-slate-900 dark:text-white hidden sm:block tracking-tight">
            Game On Tabletop
          </span>
        </router-link>

        <!-- Desktop nav links -->
        <nav class="hidden md:flex items-center gap-1 flex-1 ml-4">
          <NavItem to="/dashboard">Dashboard</NavItem>
          <NavItem to="/collection">Games</NavItem>
          <NavItem to="/friends">Friends</NavItem>
        </nav>

        <!-- Right side controls -->
        <div class="flex items-center gap-2">
          <!-- Dark mode toggle -->
          <button
            @click="toggle"
            class="w-9 h-9 flex items-center justify-center rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            :aria-label="scheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
          >
            <SunIcon v-if="scheme === 'dark'" class="w-5 h-5" />
            <MoonIcon v-else class="w-5 h-5" />
          </button>

          <!-- Avatar + dropdown -->
          <div class="relative" ref="dropdownRef">
            <button
              @click="dropdownOpen = !dropdownOpen"
              class="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
              aria-haspopup="true"
              :aria-expanded="dropdownOpen"
            >
              <BaseAvatar :src="user?.avatar_url" :name="user?.display_name || user?.username || '?'" size="sm" />
              <span class="text-sm font-medium text-slate-700 dark:text-slate-200 hidden sm:block max-w-[120px] truncate">
                {{ user?.display_name || user?.username || "Account" }}
              </span>
              <ChevronDownIcon class="w-4 h-4 text-slate-400 hidden sm:block" />
            </button>

            <Transition
              enter-active-class="transition ease-out duration-100"
              enter-from-class="opacity-0 scale-95"
              enter-to-class="opacity-100 scale-100"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="opacity-100 scale-100"
              leave-to-class="opacity-0 scale-95"
            >
              <div
                v-if="dropdownOpen"
                class="absolute right-0 mt-1 w-48 origin-top-right bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-card-hover py-1 z-50"
                role="menu"
              >
                <router-link
                  to="/profile"
                  @click="dropdownOpen = false"
                  class="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
                  role="menuitem"
                >
                  <UserCircleIcon class="w-4 h-4 text-slate-400" />
                  Profile
                </router-link>
                <div class="border-t border-slate-100 dark:border-slate-700 my-1" />
                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                  role="menuitem"
                >
                  <ArrowRightOnRectangleIcon class="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </Transition>
          </div>

          <!-- Hamburger (mobile) -->
          <button
            @click="drawerOpen = true"
            class="md:hidden w-9 h-9 flex items-center justify-center rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Open navigation"
          >
            <Bars3Icon class="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>

    <!-- Mobile drawer -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="drawerOpen" class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
          <div class="absolute inset-0 bg-black/40" @click="drawerOpen = false" />
          <Transition
            enter-active-class="transition-transform duration-200"
            enter-from-class="translate-x-full"
            enter-to-class="translate-x-0"
            leave-active-class="transition-transform duration-150"
            leave-from-class="translate-x-0"
            leave-to-class="translate-x-full"
          >
            <div v-if="drawerOpen" class="relative w-72 bg-white dark:bg-slate-800 h-full flex flex-col shadow-xl">
              <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-white">Menu</span>
                <button
                  @click="drawerOpen = false"
                  class="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                  aria-label="Close navigation"
                >
                  <XMarkIcon class="w-5 h-5" />
                </button>
              </div>
              <nav class="flex flex-col gap-1 p-4 flex-1">
                <DrawerItem to="/dashboard" @click="drawerOpen = false">
                  <HomeIcon class="w-5 h-5" /> Dashboard
                </DrawerItem>
                <DrawerItem to="/collection" @click="drawerOpen = false">
                  <PuzzlePieceIcon class="w-5 h-5" /> Games
                </DrawerItem>
                <DrawerItem to="/friends" @click="drawerOpen = false">
                  <UserGroupIcon class="w-5 h-5" /> Friends
                </DrawerItem>
                <div class="border-t border-slate-200 dark:border-slate-700 my-2" />
                <DrawerItem to="/profile" @click="drawerOpen = false">
                  <UserCircleIcon class="w-5 h-5" /> Profile
                </DrawerItem>
              </nav>
              <div class="p-4 border-t border-slate-200 dark:border-slate-700">
                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                >
                  <ArrowRightOnRectangleIcon class="w-5 h-5" /> Sign out
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!-- Page content -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs text-slate-400">
        <span>© {{ year }} Game On Tabletop</span>
        <nav class="flex gap-4">
          <a href="#" class="hover:text-slate-600 dark:hover:text-slate-200">About</a>
          <a href="#" class="hover:text-slate-600 dark:hover:text-slate-200">Contact</a>
          <a href="#" class="hover:text-slate-600 dark:hover:text-slate-200">Terms</a>
          <a href="#" class="hover:text-slate-600 dark:hover:text-slate-200">Privacy</a>
        </nav>
      </div>
    </footer>

    <ToastNotification />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  ChevronDownIcon,
  HomeIcon,
  MoonIcon,
  PuzzlePieceIcon,
  SunIcon,
  UserCircleIcon,
  UserGroupIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import ToastNotification from "../components/ui/ToastNotification.vue";
import { useColorScheme } from "../composables/useColorScheme.js";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { logout } from "../services/auth.js";

const router = useRouter();
const { scheme, toggle } = useColorScheme();
const { user, clearUser } = useCurrentUser();

const dropdownOpen = ref(false);
const drawerOpen = ref(false);
const dropdownRef = ref(null);
const year = new Date().getFullYear();

async function handleLogout() {
  dropdownOpen.value = false;
  drawerOpen.value = false;
  clearUser();
  await logout();
  router.push("/login");
}

function onClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    dropdownOpen.value = false;
  }
}

function onKeydown(e) {
  if (e.key === "Escape") {
    dropdownOpen.value = false;
    drawerOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", onClickOutside);
  document.addEventListener("keydown", onKeydown);
});
onUnmounted(() => {
  document.removeEventListener("click", onClickOutside);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<script>
import { defineComponent, h, resolveComponent } from "vue";

const NavItem = defineComponent({
  props: { to: String },
  setup(props, { slots }) {
    return () => {
      const RouterLink = resolveComponent("RouterLink");
      return h(RouterLink, {
        to: props.to,
        class: "px-3 py-2 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
        activeClass: "bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300",
      }, slots.default);
    };
  },
});

const DrawerItem = defineComponent({
  props: { to: String },
  setup(props, { slots }) {
    return () => {
      const RouterLink = resolveComponent("RouterLink");
      return h(RouterLink, {
        to: props.to,
        class: "flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
        activeClass: "bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300",
      }, slots.default);
    };
  },
});

export { DrawerItem, NavItem };
</script>
