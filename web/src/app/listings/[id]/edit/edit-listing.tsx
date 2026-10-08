"use client";

import Link from "next/link";
import { useEffect, useId, useState, type ChangeEvent, type FormEvent } from "react";

import {
  AddPhotoTile,
  FieldError,
  ListingFields,
  PhotoTile,
  errorsAfterChange,
  formIds,
  isFreeCategory,
  labelClass,
  otherErrors,
  readListingFields,
  refusalMessage,
  screenPhotos,
  toFieldErrors,
  useItemCategories,
  type Errors,
} from "@/components/listings/listing-form";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { MAX_PHOTOS, STATUS_LABELS } from "@/lib/listing-options";
import { centsToDollars } from "@/lib/money";

type Listing = components["schemas"]["Listing"];
type ListingUpdate = components["schemas"]["PatchedListingUpdateRequest"];
type ItemDetailsUpdate = components["schemas"]["ItemDetailsUpdateRequest"];
type ListingPhotoUploadRequest = components["schemas"]["ListingPhotoUploadRequest"];

const MY_LISTINGS_HREF = "/listings/mine";
const OFFLINE = "Couldn't reach Tanu. Check your connection and try again.";
const NOT_FOUND = "This listing doesn't exist.";

type Loaded =
  | { state: "loading" }
  | { state: "blocked"; message: string }
  | { state: "ready"; listing: Listing };

/** Loads the listing and the signed-in user, and shows the edit form only to the seller of an
 * Available listing. Everyone else gets a message instead. */
export function EditListing({ listingId }: { listingId: number }) {
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.GET("/api/listings/{id}/", { params: { path: { id: listingId } } }),
      api.GET("/api/me/"),
    ])
      .then(([listing, me]) => {
        if (cancelled) return;
        setLoaded(loadedFrom(listing.data, listing.response.status, me.data?.id));
      })
      .catch(() => {
        if (!cancelled) setLoaded(blocked("Couldn't reach Tanu. Check your connection and refresh."));
      });
    return () => {
      cancelled = true;
    };
  }, [listingId]);

  return (
    <>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Edit listing</h1>
        <Link
          href={MY_LISTINGS_HREF}
          className="text-sm font-medium text-foreground/70 hover:text-foreground"
        >
          My listings
        </Link>
      </div>
      {loaded.state === "loading" && <p className="mt-4 text-sm text-foreground/60">Loading…</p>}
      {loaded.state === "blocked" && (
        <p className="mt-4 text-sm text-foreground/70">{loaded.message}</p>
      )}
      {loaded.state === "ready" && <EditListingForm initial={loaded.listing} />}
    </>
  );
}

function blocked(message: string): Loaded {
  return { state: "blocked", message };
}

function loadedFrom(
  listing: Listing | undefined,
  status: number,
  myId: number | undefined,
): Loaded {
  if (status === 403) return blocked("Sign in with your school email to edit your listings.");
  if (status === 404) return blocked(NOT_FOUND);
  if (!listing || myId === undefined) {
    return blocked("Couldn't load this listing. Refresh to try again.");
  }
  // Nothing links non-sellers here, so answer a typed-in URL as if the listing weren't there.
  if (listing.seller.id !== myId) return blocked(NOT_FOUND);
  if (listing.status !== "available") {
    return blocked(
      `This listing is ${STATUS_LABELS[listing.status]}, so it can't be edited. ` +
        "Only Available listings can be edited.",
    );
  }
  return { state: "ready", listing };
}

/** Photos in display order: by position, so the cover comes first. */
function sortedPhotos(listing: Listing) {
  return [...listing.photos].sort((a, b) => a.position - b.position);
}

/** The price as the seller would type it: "25", "24.99", "1,200.50". Blank for Free. */
function priceText(cents: number) {
  return cents === 0 ? "" : centsToDollars(cents).slice(1);
}

/** API field errors, with item details' errors moved up to their own fields. */
function editErrors(body: unknown): Errors {
  const { item_details: details, ...rest } = (body ?? {}) as Record<string, unknown>;
  const nested = details && typeof details === "object" && !Array.isArray(details) ? details : {};
  return toFieldErrors({ ...rest, ...nested });
}

function EditListingForm({ initial }: { initial: Listing }) {
  const formId = useId();
  const { fieldId, errorId, fieldOf } = formIds(formId);

  const { categories: active, loadError } = useItemCategories();
  // A listing posted in a category that was later retired keeps it as an option.
  const categories =
    active && !active.some((c) => c.id === initial.category.id)
      ? [...active, initial.category]
      : active;

  const [listing, setListing] = useState(initial);
  const [categoryId, setCategoryId] = useState(String(initial.category.id));
  const [price, setPrice] = useState(priceText(initial.price_cents));
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [photoBusy, setPhotoBusy] = useState<"uploading" | "updating" | null>(null);

  const photos = sortedPhotos(listing);
  const listingPath = { params: { path: { id: listing.id } } };
  // Every request returns the whole listing, so one at a time: a slower earlier response
  // mustn't overwrite a newer one.
  const busy = saving || photoBusy !== null;

  /** A photo request's outcome: the listing it returns, or its errors shown under the photos. */
  async function photoRequest(
    send: () => Promise<{ data?: Listing; error?: unknown; response: Response }>,
  ): Promise<boolean> {
    try {
      const { data, error, response } = await send();
      if (data) {
        setListing(data);
        return true;
      }
      const problem = toFieldErrors(error);
      const messages =
        response.status === 400
          ? Object.values(problem).flatMap((m) => m ?? [])
          : [
              refusalMessage(response.status, problem.detail?.[0], {
                failed: "Couldn't update the photos. Try again.",
                signIn: "Sign in to edit your listing.",
              }),
            ];
      setErrors((current) => ({ ...current, photos: messages }));
      if (response.status === 400 || response.status === 404) {
        // The photos may have changed elsewhere (another tab); show what's there now.
        const fresh = await api.GET("/api/listings/{id}/", listingPath);
        if (fresh.data) setListing(fresh.data);
      }
    } catch {
      setErrors((current) => ({ ...current, photos: [OFFLINE] }));
    }
    return false;
  }

  async function addPhotos(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = ""; // so picking the same file again still fires onChange
    const { accepted, problems } = screenPhotos(picked, MAX_PHOTOS - photos.length);
    setErrors((current) => ({ ...current, photos: problems.length ? problems : undefined }));
    if (!accepted.length) return;
    setPhotoBusy("uploading");
    // One request per photo, in the order picked; stop at the first failure.
    for (const file of accepted) {
      const body = new FormData();
      body.set("photo", file);
      const ok = await photoRequest(() =>
        api.POST("/api/listings/{id}/photos/", {
          ...listingPath,
          // Sent as this multipart FormData; the generated type describes the file as a string.
          body: {} as ListingPhotoUploadRequest,
          bodySerializer: () => body,
        }),
      );
      if (!ok) break;
    }
    setPhotoBusy(null);
  }

  async function deletePhoto(index: number) {
    setErrors((current) => ({ ...current, photos: undefined }));
    setPhotoBusy("updating");
    await photoRequest(() =>
      api.DELETE("/api/listings/{id}/photos/{photo_id}/", {
        params: { path: { id: listing.id, photo_id: photos[index].id } },
      }),
    );
    setPhotoBusy(null);
  }

  async function movePhoto(index: number, by: -1 | 1) {
    const ids = photos.map((photo) => photo.id);
    [ids[index], ids[index + by]] = [ids[index + by], ids[index]];
    setErrors((current) => ({ ...current, photos: undefined }));
    setPhotoBusy("updating");
    await photoRequest(() =>
      api.PUT("/api/listings/{id}/photos/order/", { ...listingPath, body: { photo_ids: ids } }),
    );
    setPhotoBusy(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(false);
    const read = readListingFields(new FormData(event.currentTarget), {
      categoryId,
      price,
      isFree: isFreeCategory(categories, categoryId),
    });
    if (!read.values) {
      setErrors((current) => ({ photos: current.photos, ...read.errors }));
      return;
    }
    const { condition, size, brand, color, ...fields } = read.values;
    const body: ListingUpdate = {
      ...fields,
      // The form's choices come from the generated enums (see listing-options).
      item_details: { condition, size, brand, color } as ItemDetailsUpdate,
    };

    setSaving(true);
    try {
      const { data, error, response } = await api.PATCH("/api/listings/{id}/", {
        ...listingPath,
        body,
      });
      if (data) {
        setListing(data);
        setErrors((current) => ({ photos: current.photos }));
        setSaved(true);
      } else if (response.status === 400) {
        setErrors((current) => ({ photos: current.photos, ...editErrors(error) }));
      } else {
        const detail = toFieldErrors(error).detail?.[0];
        setErrors((current) => ({
          photos: current.photos,
          form: [
            refusalMessage(response.status, detail, {
              failed: "Couldn't save your changes. Try again.",
              signIn: "Sign in to edit your listing.",
            }),
          ],
        }));
      }
    } catch {
      setErrors((current) => ({ photos: current.photos, form: [OFFLINE] }));
    }
    setSaving(false);
  }

  if (loadError) {
    return <p className="mt-4 text-sm text-foreground/70">{loadError}</p>;
  }

  function onFormChange(event: ChangeEvent<HTMLFormElement>) {
    setSaved(false);
    const remaining = errorsAfterChange(errors, fieldOf(event.target.id));
    if (remaining) setErrors(remaining);
  }

  const formErrors = otherErrors(errors);

  return (
    <form onSubmit={save} onChange={onFormChange} noValidate className="mt-4 space-y-6">
      <fieldset>
        <legend className={labelClass}>Photos</legend>
        <p className="text-sm text-foreground/60">
          Up to {MAX_PHOTOS}. The first one is the cover. Photo changes save right away.
        </p>
        <ul aria-busy={photoBusy !== null} className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
          {photos.map((photo, index) => (
            <PhotoTile
              key={photo.id}
              src={photo.thumbnail_url ?? photo.image_url}
              index={index}
              count={photos.length}
              onRemove={() => deletePhoto(index)}
              removeLabel="Delete"
              canRemove={photos.length > 1}
              onMove={(by) => movePhoto(index, by)}
              disabled={busy}
            />
          ))}
          {photos.length < MAX_PHOTOS && (
            <AddPhotoTile
              inputId={fieldId("photos")}
              describedBy={errors.photos?.length ? errorId("photos") : undefined}
              onChange={addPhotos}
              busy={photoBusy === "uploading"}
              disabled={busy}
            />
          )}
        </ul>
        {photos.length === 1 && (
          <p className="mt-1 text-sm text-foreground/60">
            A listing needs at least one photo. Add another to replace this one.
          </p>
        )}
        <FieldError id={errorId("photos")} messages={errors.photos} />
      </fieldset>

      <ListingFields
        formId={formId}
        errors={errors}
        categories={categories}
        categoryId={categoryId}
        onCategoryChange={setCategoryId}
        price={price}
        onPriceChange={setPrice}
        initial={{
          title: initial.title,
          description: initial.description,
          condition: initial.item_details?.condition,
          size: initial.item_details?.size,
          brand: initial.item_details?.brand,
          color: initial.item_details?.color,
        }}
      />

      {formErrors.length > 0 && (
        <ul role="alert" className="space-y-0.5 text-sm text-red-600 dark:text-red-400">
          {formErrors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <button
          type="submit"
          disabled={busy || !categories}
          className="w-full rounded-full bg-foreground px-6 py-3 text-base font-semibold text-background disabled:opacity-60 sm:w-auto"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
        <p role="status" className="text-sm text-green-700 dark:text-green-400">
          {saved ? "Changes saved." : ""}
        </p>
      </div>
    </form>
  );
}
