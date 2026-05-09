import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../services/auth.js";

const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/login",
    component: () => import("../pages/LoginPage.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/register",
    component: () => import("../pages/RegisterPage.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/forgot-password",
    component: () => import("../pages/ForgotPasswordPage.vue"),
  },
  {
    path: "/reset-password",
    component: () => import("../pages/ResetPasswordPage.vue"),
  },
  {
    path: "/verify-email",
    component: () => import("../pages/VerifyEmailPage.vue"),
  },
  {
    path: "/profile",
    component: () => import("../pages/ProfilePage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/dashboard",
    component: () => import("../pages/DashboardPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/groups/new",
    component: () => import("../pages/GroupNewPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/groups/:id",
    component: () => import("../pages/GroupPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/groups/:id/series/new",
    component: () => import("../pages/SeriesNewPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/series/:id",
    component: () => import("../pages/SeriesPage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/occurrences/:id",
    component: () => import("../pages/OccurrencePage.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/invites/:token",
    component: () => import("../pages/InvitePage.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const authed = isAuthenticated();
  if (to.meta.requiresAuth && !authed) return "/login";
  if (to.meta.guestOnly && authed) return "/dashboard";
});

export default router;
