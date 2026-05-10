import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../services/auth.js";

const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/login",
    component: () => import("../pages/LoginPage.vue"),
    meta: { layout: "auth", guestOnly: true, title: "Sign in" },
  },
  {
    path: "/register",
    component: () => import("../pages/RegisterPage.vue"),
    meta: { layout: "auth", guestOnly: true, title: "Create account" },
  },
  {
    path: "/forgot-password",
    component: () => import("../pages/ForgotPasswordPage.vue"),
    meta: { layout: "auth", title: "Forgot password" },
  },
  {
    path: "/reset-password",
    component: () => import("../pages/ResetPasswordPage.vue"),
    meta: { layout: "auth", title: "Reset password" },
  },
  {
    path: "/verify-email",
    component: () => import("../pages/VerifyEmailPage.vue"),
    meta: { layout: "auth", title: "Verify email" },
  },
  {
    path: "/profile",
    component: () => import("../pages/ProfilePage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Profile" },
  },
  {
    path: "/dashboard",
    component: () => import("../pages/DashboardPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Dashboard" },
  },
  {
    path: "/groups/new",
    component: () => import("../pages/GroupNewPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "New group" },
  },
  {
    path: "/groups/:id",
    component: () => import("../pages/GroupPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Group" },
  },
  {
    path: "/groups/:id/series/new",
    component: () => import("../pages/SeriesNewPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "New series" },
  },
  {
    path: "/series/:id",
    component: () => import("../pages/SeriesPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Series" },
  },
  {
    path: "/occurrences/:id",
    component: () => import("../pages/OccurrencePage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Night" },
  },
  {
    path: "/series/:id/poll/new",
    component: () => import("../pages/PollNewPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "New poll" },
  },
  {
    path: "/polls/:id",
    component: () => import("../pages/PollPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Poll" },
  },
  {
    path: "/explore",
    component: () => import("../pages/ExplorePage.vue"),
    meta: { layout: "none", title: "Explore" },
  },
  {
    path: "/events/:id",
    component: () => import("../pages/PublicEventPage.vue"),
    meta: { layout: "none", title: "Event" },
  },
  {
    path: "/users/:username",
    component: () => import("../pages/PublicProfilePage.vue"),
    meta: { layout: "none", title: "Profile" },
  },
  {
    path: "/rsvp/:token",
    component: () => import("../pages/GuestRsvpPage.vue"),
    meta: { layout: "none", title: "RSVP" },
  },
  {
    path: "/poll-respond/:token",
    component: () => import("../pages/GuestPollPage.vue"),
    meta: { layout: "none", title: "Poll response" },
  },
  {
    path: "/collection",
    component: () => import("../pages/CollectionPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "My Collection" },
  },
  {
    path: "/friends",
    component: () => import("../pages/FriendsPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Friends" },
  },
  {
    path: "/friends/games",
    component: () => import("../pages/FriendsGamesPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Friends' Games" },
  },
  {
    path: "/users/:userId/collection",
    component: () => import("../pages/FriendCollectionPage.vue"),
    meta: { layout: "app", requiresAuth: true, title: "Collection" },
  },
  {
    path: "/invites/:token",
    component: () => import("../pages/InvitePage.vue"),
    meta: { layout: "auth", title: "Join group" },
  },
  {
    path: "/friend-invite/:token",
    component: () => import("../pages/FriendInvitePage.vue"),
    meta: { layout: "auth", title: "Friend invite" },
  },
  {
    path: "/:pathMatch(.*)*",
    component: () => import("../pages/NotFoundPage.vue"),
    meta: { layout: "auth", title: "Page not found" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const authed = isAuthenticated();
  if (to.meta.requiresAuth && !authed) return `/login?next=${encodeURIComponent(to.fullPath)}`;
  if (to.meta.guestOnly && authed) return "/dashboard";
});

router.afterEach((to) => {
  const title = to.meta.title ? `${to.meta.title} — Game On Tabletop` : "Game On Tabletop";
  document.title = title;
});

export default router;
