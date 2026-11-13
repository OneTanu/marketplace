import styles from "./price-tag.module.css";

/**
 * The kraft hang tag. On a listing card it hangs off the bottom edge of the photo, half on and
 * half off, so it never covers the item (spec 1c, G1). Put it inside a `relative` wrapper around
 * the photo, after the photo. `was` shows an older price struck through behind it.
 */
export function PriceTag({ label, was, hanging = true, className = "" }: { label: string; was?: string; hanging?: boolean; className?: string }) {
  return (
    <span className={`${styles.wrap} ${hanging ? styles.hanging : ""} ${className}`}>
      {was && <span className={`${styles.tag} ${styles.was}`}><span className="sr-only">Was </span>{was}</span>}
      <span className={`${styles.tag} ${was ? styles.drop : ""}`}>
        {was && <span className="sr-only">Now </span>}
        <span className="type-wide">{label}</span>
      </span>
    </span>
  );
}
