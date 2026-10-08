"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import {
  COLORS,
  CONDITIONS,
  FREE_CATEGORY_SLUG,
  MAX_PHOTO_BYTES,
  MAX_PHOTOS,
  PHOTO_TYPES,
} from "@/lib/listing-options";
import { dollarsToCents } from "@/lib/money";

type Category = components["schemas"]["Category"];
type ListingCreateRequest = components["schemas"]["ListingCreateRequest"];
type Photo = { file: File; url: string };
type Errors = Partial<Record<string, string[]>>;

const PROHIBITED =
  "weapons, alcohol, tobacco and vapes, drugs and prescriptions, food, counterfeits, or stolen goods";

// Where sellers land after posting. My listings (#9) will replace this.
const AFTER_POST_HREF = "/profile";

// Fields whose errors show next to their input; any other error shows above the submit button.
const FIELDS = new Set([
  "photos",
  "title",
  "description",
  "category",
  "price_cents",
  "condition",
  "size",
  "brand",
  "color",
]);

/** DRF field errors ({"title": ["..."]}, nested lists or {"0": [...]} for list items) as flat lists. */
function toFieldErrors(body: unknown): Errors {
  if (!body || typeof body !== "object") return {};
  const flatten = (value: unknown): string[] =>
    typeof value === "string"
      ? [value]
      : Array.isArray(value)
        ? value.flatMap(flatten)
        : value && typeof value === "object"
          ? Object.values(value).flatMap(flatten)
          : [];
  return Object.fromEntries(Object.entries(body).map(([field, value]) => [field, flatten(value)]));
}

/** Text for a non-validation failure. 403 details from Django are shown only when written for
 * people (e.g. an account without a school), not CSRF or sign-in internals. */
function refusalMessage(status: number, detail?: string): string {
  if (status !== 403 || !detail) return "Couldn't post your listing. Try again.";
  if (detail.startsWith("CSRF")) return "Your session expired. Refresh the page and try again.";
  if (detail.startsWith("Authentication credentials")) return "Sign in to post a listing.";
  return detail;
}

function FieldError({ id, messages }: { id: string; messages?: string[] }) {
  if (!messages?.length) return null;
  return (
    <ul id={id} className="mt-1 space-y-0.5 text-sm text-red-600 dark:text-red-400">
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
}

const inputClass =
  "mt-1 block w-full rounded-lg border border-black/15 bg-background px-3 py-2.5 text-base outline-none focus:border-foreground disabled:opacity-60 aria-[invalid=true]:border-red-600 dark:border-white/20";
const labelClass = "block text-sm font-medium";

export function SellForm() {
  const router = useRouter();
  const formId = useId();
  const fieldId = (name: string) => `${formId}-${name}`;
  const errorId = (name: string) => `${formId}-${name}-error`;

  const [categories, setCategories] = useState<Category[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [price, setPrice] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);

  // Every preview URL ever created, so they can be released when the form goes away.
  const previewUrls = useRef(new Set<string>());
  useEffect(() => {
    const urls = previewUrls.current;
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/categories/", { params: { query: { kind: "item" } } })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) setCategories(data);
        else if (response.status === 403) setLoadError("Sign in with your school email to sell.");
        else setLoadError("Couldn't load categories. Refresh to try again.");
      })
      .catch(() => {
        if (!cancelled) setLoadError("Couldn't reach Tanu. Check your connection and refresh.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const category = categories?.find((c) => String(c.id) === categoryId);
  const isFree = category?.slug === FREE_CATEGORY_SLUG;

  function addPhotos(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = ""; // so picking the same file again still fires onChange
    const problems: string[] = [];
    const accepted: Photo[] = [];
    for (const file of picked) {
      if (!PHOTO_TYPES.includes(file.type)) {
        problems.push(`${file.name} isn't a JPEG, PNG or WebP image.`);
      } else if (file.size > MAX_PHOTO_BYTES) {
        problems.push(`${file.name} is larger than 10 MB.`);
      } else if (photos.length + accepted.length >= MAX_PHOTOS) {
        problems.push(`You can add up to ${MAX_PHOTOS} photos.`);
        break;
      } else {
        const url = URL.createObjectURL(file);
        previewUrls.current.add(url);
        accepted.push({ file, url });
      }
    }
    setPhotos([...photos, ...accepted]);
    setErrors({ ...errors, photos: problems.length ? problems : undefined });
  }

  function removePhoto(index: number) {
    URL.revokeObjectURL(photos[index].url);
    previewUrls.current.delete(photos[index].url);
    setPhotos(photos.filter((_, i) => i !== index));
    // Photo errors refer to photos by number, which just shifted.
    setErrors({ ...errors, photos: undefined });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (name: string) => String(form.get(name) ?? "").trim();

    const priceCents = isFree ? 0 : dollarsToCents(price);
    const found: Errors = {};
    if (!photos.length) found.photos = ["Add at least one photo."];
    if (!text("title")) found.title = ["Add a title."];
    if (!categoryId) found.category = ["Choose a category."];
    if (priceCents === null) found.price_cents = ["Enter a price like 25 or 24.99."];
    if (!text("condition")) found.condition = ["Choose a condition."];
    setErrors(found);
    if (Object.keys(found).length || priceCents === null) return;

    const body = new FormData();
    body.set("title", text("title"));
    body.set("description", text("description"));
    body.set("category", categoryId);
    body.set("price_cents", String(priceCents));
    body.set("condition", text("condition"));
    body.set("size", text("size"));
    body.set("brand", text("brand"));
    body.set("color", text("color"));
    for (const photo of photos) body.append("photos", photo.file);

    setSubmitting(true);
    try {
      const { data, error, response } = await api.POST("/api/listings/", {
        // The request goes out as this multipart FormData. The generated type describes
        // files as strings, so the typed body is only there to satisfy the client.
        body: {} as ListingCreateRequest,
        bodySerializer: () => body,
      });
      if (data) {
        router.push(AFTER_POST_HREF);
        return;
      }
      const problem: unknown = error;
      if (response.status === 400) {
        setErrors(toFieldErrors(problem));
      } else {
        setErrors({ form: [refusalMessage(response.status, toFieldErrors(problem).detail?.[0])] });
      }
    } catch {
      setErrors({ form: ["Couldn't reach Tanu. Check your connection and try again."] });
    }
    setSubmitting(false);
  }

  if (loadError) {
    return <p className="mt-4 text-sm text-foreground/70">{loadError}</p>;
  }

  // Editing a field clears its error, so a fixed field doesn't stay red until the next submit.
  // Changing the category also clears the price error (the Free/$0 rule depends on it).
  function clearErrorFor(event: ChangeEvent<HTMLFormElement>) {
    const field = event.target.id?.slice(formId.length + 1);
    if (!field || field === "photos") return; // photo errors are handled in addPhotos/removePhoto
    const keys =
      field === "price"
        ? ["price_cents"]
        : field === "category"
          ? ["category", "price_cents"]
          : [field];
    if (!keys.some((key) => errors[key])) return;
    setErrors(Object.fromEntries(Object.entries(errors).filter(([key]) => !keys.includes(key))));
  }

  const invalid = (name: string) => (errors[name]?.length ? true : undefined);
  const describedBy = (name: string) => (errors[name]?.length ? errorId(name) : undefined);
  const otherErrors = Object.entries(errors)
    .filter(([field]) => !FIELDS.has(field))
    .flatMap(([, messages]) => messages ?? []);

  return (
    <form onSubmit={submit} onChange={clearErrorFor} noValidate className="mt-4 space-y-6">
      <fieldset>
        <legend className={labelClass}>Photos</legend>
        <p className="text-sm text-foreground/60">
          Up to {MAX_PHOTOS}. The first one is the cover.
        </p>
        <ul className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
          {photos.map((photo, index) => (
            <li
              key={photo.url}
              className="relative aspect-square overflow-hidden rounded-lg bg-foreground/5"
            >
              <Image
                src={photo.url}
                alt={`Photo ${index + 1}`}
                fill
                unoptimized
                className="object-cover"
              />
              {index === 0 && (
                <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white">
                  Cover
                </span>
              )}
              <button
                type="button"
                onClick={() => removePhoto(index)}
                aria-label={`Remove photo ${index + 1}`}
                className="absolute right-1 top-1 flex size-7 items-center justify-center rounded-full bg-black/70 text-white"
              >
                <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path d="M6 6l12 12M18 6 6 18" />
                </svg>
              </button>
            </li>
          ))}
          {photos.length < MAX_PHOTOS && (
            <li>
              <label
                htmlFor={fieldId("photos")}
                className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-black/20 text-sm text-foreground/70 hover:bg-foreground/5 dark:border-white/25"
              >
                <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Add photos
              </label>
              <input
                id={fieldId("photos")}
                type="file"
                accept={PHOTO_TYPES.join(",")}
                multiple
                onChange={addPhotos}
                aria-describedby={describedBy("photos")}
                className="sr-only"
              />
            </li>
          )}
        </ul>
        <FieldError id={errorId("photos")} messages={errors.photos} />
      </fieldset>

      <div>
        <label htmlFor={fieldId("title")} className={labelClass}>
          Title
        </label>
        <input
          id={fieldId("title")}
          name="title"
          maxLength={120}
          placeholder="e.g. North Face puffer jacket"
          aria-invalid={invalid("title")}
          aria-describedby={describedBy("title")}
          className={inputClass}
        />
        <FieldError id={errorId("title")} messages={errors.title} />
      </div>

      <div>
        <label htmlFor={fieldId("description")} className={labelClass}>
          Description <span className="font-normal text-foreground/60">(optional)</span>
        </label>
        <textarea
          id={fieldId("description")}
          name="description"
          rows={4}
          maxLength={5000}
          placeholder="Condition details, measurements, pickup spot…"
          aria-invalid={invalid("description")}
          aria-describedby={describedBy("description")}
          className={inputClass}
        />
        <FieldError id={errorId("description")} messages={errors.description} />
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor={fieldId("category")} className={labelClass}>
            Category
          </label>
          <select
            id={fieldId("category")}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            disabled={!categories}
            aria-invalid={invalid("category")}
            aria-describedby={describedBy("category")}
            className={inputClass}
          >
            <option value="">{categories ? "Choose a category" : "Loading…"}</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <FieldError id={errorId("category")} messages={errors.category} />
        </div>

        <div>
          <label htmlFor={fieldId("price")} className={labelClass}>
            Price
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center pt-1 text-foreground/60">
              $
            </span>
            <input
              id={fieldId("price")}
              inputMode="decimal"
              autoComplete="off"
              placeholder="0.00"
              value={isFree ? "0" : price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={isFree}
              aria-invalid={invalid("price_cents")}
              aria-describedby={describedBy("price_cents")}
              className={`${inputClass} pl-7`}
            />
          </div>
          {isFree && <p className="mt-1 text-sm text-foreground/60">Items in Free are always $0.</p>}
          <FieldError id={errorId("price_cents")} messages={errors.price_cents} />
        </div>
      </div>

      <div>
        <label htmlFor={fieldId("condition")} className={labelClass}>
          Condition
        </label>
        <select
          id={fieldId("condition")}
          name="condition"
          defaultValue=""
          aria-invalid={invalid("condition")}
          aria-describedby={describedBy("condition")}
          className={inputClass}
        >
          <option value="">Choose a condition</option>
          {CONDITIONS.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <FieldError id={errorId("condition")} messages={errors.condition} />
      </div>

      <fieldset className="space-y-4">
        <legend className={labelClass}>
          Details <span className="font-normal text-foreground/60">(optional)</span>
        </legend>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor={fieldId("size")} className="block text-sm text-foreground/70">
              Size
            </label>
            <input
              id={fieldId("size")}
              name="size"
              maxLength={30}
              placeholder="e.g. M, 32x30, Twin XL"
              aria-invalid={invalid("size")}
              aria-describedby={describedBy("size")}
              className={inputClass}
            />
            <FieldError id={errorId("size")} messages={errors.size} />
          </div>
          <div>
            <label htmlFor={fieldId("brand")} className="block text-sm text-foreground/70">
              Brand
            </label>
            <input
              id={fieldId("brand")}
              name="brand"
              maxLength={100}
              aria-invalid={invalid("brand")}
              aria-describedby={describedBy("brand")}
              className={inputClass}
            />
            <FieldError id={errorId("brand")} messages={errors.brand} />
          </div>
          <div>
            <label htmlFor={fieldId("color")} className="block text-sm text-foreground/70">
              Color
            </label>
            <select
              id={fieldId("color")}
              name="color"
              defaultValue=""
              aria-invalid={invalid("color")}
              aria-describedby={describedBy("color")}
              className={inputClass}
            >
              <option value="">None</option>
              {COLORS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <FieldError id={errorId("color")} messages={errors.color} />
          </div>
        </div>
      </fieldset>

      <p className="rounded-lg bg-foreground/5 p-3 text-sm text-foreground/70">
        <span className="font-medium text-foreground">Not allowed on Tanu:</span> {PROHIBITED}.
        Listings for these are removed.
      </p>

      {otherErrors.length > 0 && (
        <ul role="alert" className="space-y-0.5 text-sm text-red-600 dark:text-red-400">
          {otherErrors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}

      <button
        type="submit"
        disabled={submitting || !categories}
        className="w-full rounded-full bg-foreground px-6 py-3 text-base font-semibold text-background disabled:opacity-60 sm:w-auto"
      >
        {submitting ? "Posting…" : "Post listing"}
      </button>
    </form>
  );
}
