"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";

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
import { MAX_PHOTOS } from "@/lib/listing-options";

type ListingCreateRequest = components["schemas"]["ListingCreateRequest"];
type Photo = { file: File; url: string };

// Where sellers land after posting.
const AFTER_POST_HREF = "/listings/mine";

export function SellForm() {
  const router = useRouter();
  const formId = useId();
  const { fieldId, errorId, fieldOf } = formIds(formId);

  const { categories, loadError } = useItemCategories();
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

  function addPhotos(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = ""; // so picking the same file again still fires onChange
    const { accepted, problems } = screenPhotos(picked, MAX_PHOTOS - photos.length);
    const added = accepted.map((file) => {
      const url = URL.createObjectURL(file);
      previewUrls.current.add(url);
      return { file, url };
    });
    setPhotos([...photos, ...added]);
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
    const read = readListingFields(new FormData(event.currentTarget), {
      categoryId,
      price,
      isFree: isFreeCategory(categories, categoryId),
    });
    const found: Errors = photos.length ? {} : { photos: ["Add at least one photo."] };
    Object.assign(found, read.errors);
    setErrors(found);
    if (!read.values || Object.keys(found).length) return;

    const body = new FormData();
    for (const [field, value] of Object.entries(read.values)) body.set(field, String(value));
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
        const detail = toFieldErrors(problem).detail?.[0];
        setErrors({
          form: [
            refusalMessage(response.status, detail, {
              failed: "Couldn't post your listing. Try again.",
              signIn: "Sign in to post a listing.",
            }),
          ],
        });
      }
    } catch {
      setErrors({ form: ["Couldn't reach Tanu. Check your connection and try again."] });
    }
    setSubmitting(false);
  }

  if (loadError) {
    return <p className="mt-4 text-sm text-foreground/70">{loadError}</p>;
  }

  function clearErrorFor(event: ChangeEvent<HTMLFormElement>) {
    const remaining = errorsAfterChange(errors, fieldOf(event.target.id));
    if (remaining) setErrors(remaining);
  }

  const formErrors = otherErrors(errors);

  return (
    <form onSubmit={submit} onChange={clearErrorFor} noValidate className="mt-4 space-y-6">
      <fieldset>
        <legend className={labelClass}>Photos</legend>
        <p className="text-sm text-foreground/60">
          Up to {MAX_PHOTOS}. The first one is the cover.
        </p>
        <ul className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
          {photos.map((photo, index) => (
            <PhotoTile
              key={photo.url}
              src={photo.url}
              index={index}
              count={photos.length}
              onRemove={() => removePhoto(index)}
            />
          ))}
          {photos.length < MAX_PHOTOS && (
            <AddPhotoTile
              inputId={fieldId("photos")}
              describedBy={errors.photos?.length ? errorId("photos") : undefined}
              onChange={addPhotos}
            />
          )}
        </ul>
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
      />

      {formErrors.length > 0 && (
        <ul role="alert" className="space-y-0.5 text-sm text-red-600 dark:text-red-400">
          {formErrors.map((message) => (
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
