import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../services/auth.js";

const routes = [
  { path: "/", redirect: "/profile" },
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
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const authed = isAuthenticated();
  if (to.meta.requiresAuth && !authed) return "/login";
  if (to.meta.guestOnly && authed) return "/profile";
});

export default router;
