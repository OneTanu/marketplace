"use client";

// Pieces shared by the Sell form (create) and the edit screen: the listing fields, their
// client-side checks, error display, and the photo tiles.

import Image from "next/image";
import { useEffect, useState, type ChangeEvent } from "react";

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

export type Category = components["schemas"]["Category"];
export type Errors = Partial<Record<string, string[]>>;

const PROHIBITED =
  "weapons, alcohol, tobacco and vapes, drugs and prescriptions, food, counterfeits, or stolen goods";

// Fields whose errors show next to their input; any other error shows above the submit button.
export const FIELDS = new Set([
  "photos",
  "photo",
  "title",
  "description",
  "category",
  "price_cents",
  "condition",
  "size",
  "brand",
  "color",
]);

export const inputClass =
  "mt-1 block w-full rounded-lg border border-black/15 bg-background px-3 py-2.5 text-base outline-none focus:border-foreground disabled:opacity-60 aria-[invalid=true]:border-red-600 dark:border-white/20";
export const labelClass = "block text-sm font-medium";

/** Element ids for a form's fields and their error lists, so labels and errors line up. */
export function formIds(formId: string) {
  return {
    fieldId: (name: string) => `${formId}-${name}`,
    errorId: (name: string) => `${formId}-${name}-error`,
    /** The field name of an element with a fieldId, or undefined. */
    fieldOf: (elementId: string | undefined) =>
      elementId?.startsWith(`${formId}-`) ? elementId.slice(formId.length + 1) : undefined,
  };
}

/** DRF field errors ({"title": ["..."]}, nested lists or objects such as {"0": [...]} or
 * {"item_details": {"color": [...]}}) as flat lists per top-level field. */
export function toFieldErrors(body: unknown): Errors {
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

/** Text for a non-validation failure. 409 details explain a status conflict and are shown as
 * is; 403 details from Django are shown only when written for people (e.g. an account without
 * a school, or someone else's listing), not CSRF or sign-in internals. */
export function refusalMessage(
  status: number,
  detail: string | undefined,
  messages: { failed: string; signIn: string },
): string {
  if (status === 409 && detail) return detail;
  if (status !== 403 || !detail) return messages.failed;
  if (detail.startsWith("CSRF")) return "Your session expired. Refresh the page and try again.";
  if (detail.startsWith("Authentication credentials")) return messages.signIn;
  return detail;
}

export function FieldError({ id, messages }: { id: string; messages?: string[] }) {
  if (!messages?.length) return null;
  return (
    <ul id={id} className="mt-1 space-y-0.5 text-sm text-red-600 dark:text-red-400">
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
}

/** Errors other than the per-field ones, for showing above the submit button. */
export function otherErrors(errors: Errors): string[] {
  return Object.entries(errors)
    .filter(([field]) => !FIELDS.has(field))
    .flatMap(([, messages]) => messages ?? []);
}

/** The errors left once a field changes: editing a field clears its error, so a fixed field
 * doesn't stay red until the next submit. Changing the category also clears the price error
 * (the Free/$0 rule depends on it). Returns null when nothing needs clearing. */
export function errorsAfterChange(errors: Errors, field: string | undefined): Errors | null {
  if (!field || field === "photos") return null; // photo errors are handled by the photo controls
  const keys =
    field === "price"
      ? ["price_cents"]
      : field === "category"
        ? ["category", "price_cents"]
        : [field];
  if (!keys.some((key) => errors[key])) return null;
  return Object.fromEntries(Object.entries(errors).filter(([key]) => !keys.includes(key)));
}

/** The active item categories, loaded once. */
export function useItemCategories() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
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
  return { categories, loadError };
}

export function isFreeCategory(categories: Category[] | null, categoryId: string): boolean {
  return categories?.find((c) => String(c.id) === categoryId)?.slug === FREE_CATEGORY_SLUG;
}

export type ListingFieldValues = {
  title: string;
  description: string;
  category: number;
  price_cents: number;
  condition: string;
  size: string;
  brand: string;
  color: string;
};

/** Reads and checks the listing fields of a submitted form. The price is typed in dollars and
 * becomes integer cents (always 0 in Free). Returns the values, or the errors to show. */
export function readListingFields(
  form: FormData,
  { categoryId, price, isFree }: { categoryId: string; price: string; isFree: boolean },
): { values: ListingFieldValues; errors?: never } | { values?: never; errors: Errors } {
  const text = (name: string) => String(form.get(name) ?? "").trim();
  const priceCents = isFree ? 0 : dollarsToCents(price);
  const errors: Errors = {};
  if (!text("title")) errors.title = ["Add a title."];
  if (!categoryId) errors.category = ["Choose a category."];
  if (priceCents === null) errors.price_cents = ["Enter a price like 25 or 24.99."];
  if (!text("condition")) errors.condition = ["Choose a condition."];
  if (Object.keys(errors).length || priceCents === null) return { errors };
  return {
    values: {
      title: text("title"),
      description: text("description"),
      category: Number(categoryId),
      price_cents: priceCents,
      condition: text("condition"),
      size: text("size"),
      brand: text("brand"),
      color: text("color"),
    },
  };
}

/** Splits picked files into ones that can be uploaded (at most `room` of them) and messages
 * about the rest, checked the same way the backend will. */
export function screenPhotos(files: File[], room: number) {
  const accepted: File[] = [];
  const problems: string[] = [];
  for (const file of files) {
    if (!PHOTO_TYPES.includes(file.type)) {
      problems.push(`${file.name} isn't a JPEG, PNG or WebP image.`);
    } else if (file.size > MAX_PHOTO_BYTES) {
      problems.push(`${file.name} is larger than 10 MB.`);
    } else if (accepted.length >= room) {
      problems.push(`You can add up to ${MAX_PHOTOS} photos.`);
      break;
    } else {
      accepted.push(file);
    }
  }
  return { accepted, problems };
}

function IconButton({
  label,
  onClick,
  disabled,
  className,
  path,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className: string;
  path: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`absolute flex size-8 items-center justify-center rounded-full bg-black/70 text-white disabled:opacity-40 ${className}`}
    >
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path d={path} />
      </svg>
    </button>
  );
}

/** One photo in a photo grid. The first is the cover. Move controls show when onMove is set
 * and there's more than one photo. */
export function PhotoTile({
  src,
  index,
  count,
  onRemove,
  removeLabel = "Remove",
  canRemove = true,
  onMove,
  disabled,
}: {
  src: string;
  index: number;
  count: number;
  onRemove: () => void;
  removeLabel?: string;
  canRemove?: boolean;
  onMove?: (by: -1 | 1) => void;
  disabled?: boolean;
}) {
  const number = index + 1;
  return (
    <li className="relative aspect-square overflow-hidden rounded-lg bg-foreground/5">
      {/* unoptimized: previews are blob: URLs, and Django serves /media directly. */}
      <Image src={src} alt={`Photo ${number}`} fill unoptimized className="object-cover" />
      {index === 0 && (
        <span className="absolute left-1 top-1 rounded bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white">
          Cover
        </span>
      )}
      {canRemove && (
        <IconButton
          label={`${removeLabel} photo ${number}`}
          onClick={onRemove}
          disabled={disabled}
          className="right-1 top-1"
          path="M6 6l12 12M18 6 6 18"
        />
      )}
      {onMove && count > 1 && (
        <>
          <IconButton
            label={number === 2 ? `Make photo ${number} the cover` : `Move photo ${number} earlier`}
            onClick={() => onMove(-1)}
            disabled={disabled || index === 0}
            className="bottom-1 left-1"
            path="M15 6l-6 6 6 6"
          />
          <IconButton
            label={`Move photo ${number} later`}
            onClick={() => onMove(1)}
            disabled={disabled || index === count - 1}
            className="bottom-1 right-1"
            path="M9 6l6 6-6 6"
          />
        </>
      )}
    </li>
  );
}

/** The "Add photos" tile at the end of a photo grid. */
export function AddPhotoTile({
  inputId,
  describedBy,
  onChange,
  busy,
  disabled = busy,
}: {
  inputId: string;
  describedBy?: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  /** Shows "Uploading…" (and disables the tile). */
  busy?: boolean;
  disabled?: boolean;
}) {
  return (
    <li>
      <label
        htmlFor={inputId}
        aria-disabled={disabled || undefined}
        className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-black/20 text-sm text-foreground/70 hover:bg-foreground/5 aria-disabled:cursor-wait aria-disabled:opacity-60 dark:border-white/25"
      >
        <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
          <path d="M12 5v14M5 12h14" />
        </svg>
        {busy ? "Uploading…" : "Add photos"}
      </label>
      <input
        id={inputId}
        type="file"
        accept={PHOTO_TYPES.join(",")}
        multiple
        disabled={disabled}
        onChange={onChange}
        aria-describedby={describedBy}
        className="sr-only"
      />
    </li>
  );
}

type Initial = Partial<
  Record<"title" | "description" | "condition" | "size" | "brand" | "color", string>
>;

/** Title, description, category, price, condition and the optional details, plus the
 * prohibited-items reminder. Category and price are controlled (the Free/$0 rule ties them
 * together); the rest are read from the form on submit, starting from `initial`. */
export function ListingFields({
  formId,
  errors,
  categories,
  categoryId,
  onCategoryChange,
  price,
  onPriceChange,
  initial = {},
}: {
  formId: string;
  errors: Errors;
  categories: Category[] | null;
  categoryId: string;
  onCategoryChange: (categoryId: string) => void;
  price: string;
  onPriceChange: (price: string) => void;
  initial?: Initial;
}) {
  const { fieldId, errorId } = formIds(formId);
  const isFree = isFreeCategory(categories, categoryId);
  const invalid = (name: string) => (errors[name]?.length ? true : undefined);
  const describedBy = (name: string) => (errors[name]?.length ? errorId(name) : undefined);

  return (
    <>
      <div>
        <label htmlFor={fieldId("title")} className={labelClass}>
          Title
        </label>
        <input
          id={fieldId("title")}
          name="title"
          maxLength={120}
          defaultValue={initial.title}
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
          defaultValue={initial.description}
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
            onChange={(e) => onCategoryChange(e.target.value)}
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
              onChange={(e) => onPriceChange(e.target.value)}
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
          defaultValue={initial.condition ?? ""}
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
              defaultValue={initial.size}
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
              defaultValue={initial.brand}
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
              defaultValue={initial.color ?? ""}
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
    </>
  );
}
