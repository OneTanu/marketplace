import Image from "next/image";
import Link from "next/link";

// Photos of the kind of thing students sell, for signed-out visitors. Not listings.
const heroPhotos = [
  { src: "/demo-listings/real/tan-washed-chore-jacket.jpg", alt: "A tan canvas chore jacket" },
  { src: "/demo-listings/real/coach-signature-crossbody.jpg", alt: "A black crossbody bag" },
  { src: "/demo-listings/real/black-washed-wide-jeans.jpg", alt: "Black wide-leg jeans" },
  { src: "/demo-listings/real/timberland-wheat-boots.jpg", alt: "Wheat work boots" },
];

const departments = [
  { href: "/search?category=women", name: "Women", image: "/demo-listings/jacket.svg" },
  { href: "/search?category=men", name: "Men", image: "/demo-listings/real/faded-black-zip-hoodie.jpg" },
  { href: "/search?category=shoes", name: "Shoes", image: "/demo-listings/shoes.svg" },
  { href: "/search?category=accessories", name: "Accessories", image: "/demo-listings/tote.svg" },
];

const trustPoints = [
  { title: "Only students", text: "Every account is verified with a school email before it can buy or sell." },
  { title: "Your campus first", text: "Your feed shows items from your school, so meetups are a short walk away." },
  { title: "No shipping", text: "Message the seller, agree on a price, and hand it off in person." },
];

export default function HomePage() {
  return <div>
    <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pt-10 pb-14 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:gap-14 lg:pt-16 lg:pb-20">
      <div className="max-w-xl">
        <h1 className="type-wide text-[2.75rem] font-black leading-[0.95] text-ink sm:text-6xl lg:text-[4.5rem]">Your campus is a closet.</h1>
        <p className="mt-6 max-w-md text-lg leading-7 text-muted">Buy and sell clothes, shoes, and dorm essentials with verified students at your school.</p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/account/signup" className="btn btn-primary h-12 px-6 text-[15px]">Join with your school email</Link>
          <Link href="/search" className="btn btn-secondary h-12 px-6 text-[15px]">Start browsing</Link>
        </div>
        <p className="mt-5 text-sm text-muted">Free to join. Requires a supported school email.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4">
        {heroPhotos.map((photo, index) => <Link key={photo.src} href="/search" className={`group relative block overflow-hidden rounded-md bg-surface ${index % 2 === 1 ? "translate-y-8" : ""}`}>
          <div className="relative aspect-[4/5]"><Image src={photo.src} alt={photo.alt} fill priority={index < 2} sizes="(max-width: 1024px) 50vw, 28vw" className="object-cover transition duration-500 desktop:group-hover:scale-[1.03]" /></div>
        </Link>)}
      </div>
    </section>

    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
        <div className="flex items-end justify-between gap-4">
          <h2 className="type-wide text-2xl font-black sm:text-3xl">Shop by department</h2>
          <Link href="/search" className="text-sm font-semibold text-brand hover:underline">See everything</Link>
        </div>
        <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-5">
          {departments.map((department) => <Link key={department.name} href={department.href} className="group block">
            <div className="relative aspect-square overflow-hidden rounded-md bg-surface"><Image src={department.image} alt="" fill sizes="(max-width: 1024px) 50vw, 20vw" className="object-cover transition duration-500 desktop:group-hover:scale-[1.03]" /></div>
            <p className="mt-2.5 font-bold">{department.name}</p>
          </Link>)}
          <Link href="/search?category=dorm-furniture" className="col-span-2 flex flex-col justify-between rounded-md bg-ink p-5 text-white transition hover:bg-brand lg:col-span-1 lg:aspect-square">
            <p className="type-wide text-2xl font-black leading-tight">Campus items</p>
            <p className="mt-6 text-sm leading-6 text-white/75">Calculators, mini fridges, lamps, textbooks, and the rest of your move-in list.</p>
          </Link>
        </div>
      </div>
    </section>

    <section className="bg-surface">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-3 sm:px-6 sm:py-14">
        {trustPoints.map((point) => <div key={point.title}>
          <h2 className="type-wide text-lg font-extrabold">{point.title}</h2>
          <p className="mt-2 max-w-xs leading-6 text-muted">{point.text}</p>
        </div>)}
      </div>
    </section>
  </div>;
}
