# Avatar Upload via Supabase Storage

## Goal

Allow users to upload a profile photo directly from the Profile page. The image is stored in a Supabase Storage bucket and the resulting public CDN URL is saved to the `avatar_url` column on the `users` table. This replaces the current free-text "Avatar URL" input field.

## Background

The `users` table already has an `avatar_url varchar` column and the Profile page already renders it via `BaseAvatar`. Currently users must paste a URL manually — there is no file upload. Supabase Storage is the natural fit because the project already uses Supabase PostgreSQL, so no new vendor is needed.

---

## Data Model

No schema changes needed. `users.avatar_url` stores the Supabase Storage public URL (e.g. `https://<project>.supabase.co/storage/v1/object/public/avatars/<user-id>/<filename>`).

### Supabase Storage setup (one-time, done in Supabase dashboard)

1. Create a bucket named `avatars` — set **public** (CDN-served, no signed URLs needed)
2. Add a Storage policy: authenticated users may INSERT/UPDATE/DELETE only objects whose path begins with their own `auth.uid()` (i.e. `avatars/<user-id>/`)

---

## Backend

### New environment variable (`app/config.py`)

```
supabase_url: str = ""          # e.g. https://xyzxyz.supabase.co
supabase_service_role_key: str = ""  # service role key (never exposed to frontend)
```

### New dependency (`pyproject.toml` / `requirements.txt`)

```
supabase>=2.0.0
```

### New endpoint (`app/api/users.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/users/me/avatar` | required | Upload avatar; returns `{ avatar_url }` |

**Implementation notes:**
- Accept `multipart/form-data` with a single `file` field
- Validate: content-type must be `image/jpeg`, `image/png`, `image/webp`, or `image/gif`; max 5 MB
- Sanitise the filename: store as `<user_id>/<uuid4>.<ext>` to avoid path traversal and collisions
- Upload to Supabase Storage using the service role key via the Python `supabase` client
- On success, update `users.avatar_url` in the database and return the public URL
- Delete the previous object from Storage if a prior `avatar_url` is already set and points to the same bucket (prevent orphaned files)

### Tests (`tests/test_users.py`)

- [ ] Upload a valid PNG → 200, `avatar_url` updated in DB and returned
- [ ] Upload rejected when content-type is not an image → 415
- [ ] Upload rejected when file exceeds 5 MB → 413
- [ ] Upload rejected when unauthenticated → 401
- [ ] Subsequent upload overwrites the previous Storage object (no orphan)

---

## Frontend

### Profile page changes (`src/pages/ProfilePage.vue`)

- Replace the "Avatar URL" `BaseInput` with an **avatar picker** component:
  - Display the current avatar (or initials fallback) in a large circle
  - An "Upload photo" button overlaid on the avatar (camera icon)
  - Hidden `<input type="file" accept="image/*">` triggered by the button
  - On file selected: show a local `URL.createObjectURL` preview immediately (optimistic UI)
  - On form submit: if a new file was selected, POST it to `/api/users/me/avatar` as `multipart/form-data` before PATCHing the profile fields; use the returned `avatar_url` in the PATCH body
  - Show an inline progress/spinner while uploading
  - Show a toast error if the upload fails (size, type, network) and revert the preview

### New component (`src/components/ui/AvatarUpload.vue`)

```
props:
  src: String          – current avatar URL
  name: String         – fallback initials source
  modelValue: File     – v-model for the selected File object (null if unchanged)

emits:
  update:modelValue    – emits the File when user selects one, null if removed

template:
  <div class="relative w-24 h-24">
    <BaseAvatar :src="previewUrl || src" :name="name" size="2xl" />
    <label class="absolute inset-0 flex items-end justify-center pb-1 cursor-pointer group">
      <span class="bg-black/50 text-white text-xs rounded-full px-2 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        Change
      </span>
      <input type="file" class="sr-only" accept="image/jpeg,image/png,image/webp,image/gif" @change="onFile" />
    </label>
  </div>
```

---

## Acceptance Criteria

- [ ] Supabase `avatars` bucket created, public, with per-user path policy
- [ ] `supabase_url` and `supabase_service_role_key` added to `.env.example` and Vercel backend env vars
- [ ] `POST /api/users/me/avatar` validates file type and size before uploading
- [ ] Uploaded file stored at path `avatars/<user-id>/<uuid>.<ext>`
- [ ] Previous avatar file deleted from Storage on re-upload
- [ ] `users.avatar_url` updated in DB; returned in response
- [ ] Profile page shows avatar picker; preview updates on file selection
- [ ] Upload triggered on "Save changes" (not immediately on file pick)
- [ ] Toast shown on upload error; form remains editable
- [ ] AppShell nav avatar updates after a successful save (re-fetches `/api/users/me`)
- [ ] All existing `test_users.py` tests still pass
- [ ] New avatar upload tests pass

---

## Implementation Notes

- Use the Supabase **service role key** server-side only — never expose it to the frontend. The frontend calls the backend endpoint, not Supabase Storage directly, so the anon key is not needed for this feature.
- The `supabase` Python client wraps the Storage REST API; use `client.storage.from_("avatars").upload(path, file_bytes, {"content-type": content_type})` and `client.storage.from_("avatars").get_public_url(path)` to get the CDN URL.
- For tests, mock the Supabase client using `unittest.mock.patch` on the service layer function — avoid making real network calls in CI.
- The public URL pattern is stable once the bucket is public; no signed URLs or expiry to manage.
- Cap file size at 5 MB server-side (FastAPI `UploadFile` reads lazily; read in chunks and reject early if the total exceeds the limit).
