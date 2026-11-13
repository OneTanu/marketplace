import type { Metadata } from "next";
import Link from "next/link";

import { LegalList, LegalPage, LegalSection } from "@/components/legal-page";
import { SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: "Terms of Service", description: "The rules for buying and selling on Tanu." };

const Email = () => <a href={`mailto:${SUPPORT_EMAIL}`} className="font-semibold underline decoration-ink/30 decoration-2 underline-offset-4">{SUPPORT_EMAIL}</a>;
const PrivacyLink = () => <Link href="/privacy" className="font-semibold underline decoration-ink/30 decoration-2 underline-offset-4">Privacy Policy</Link>;

export default function TermsPage() {
  return <LegalPage
    title="Terms of Service"
    updated="November 13, 2026"
    intro={<>
      <p>These Terms are an agreement between you and the team that operates Tanu (“Tanu,” “we,” “us”). By creating an account or using tanu.one, you agree to them and to our <PrivacyLink />. If you don’t agree, please don’t use Tanu.</p>
      <p>Tanu is independent and is not affiliated with or endorsed by any university.</p>
    </>}
  >
    <LegalSection title="1. Who can use Tanu">
      <LegalList items={[
        "You must be at least 18 and a current student at a school where Tanu is open.",
        "You must sign up with your own school email address and verify it. Your school is set from that email.",
        "One account per person. Don’t share your account or sign in as someone else.",
        "You’re responsible for activity on your account. Keep your password secure and tell us right away if you think someone else has accessed it.",
      ]} />
    </LegalSection>

    <LegalSection title="2. Tanu’s role">
      <p>Tanu helps students find each other, agree on a price, and arrange a handoff. <strong>Tanu is not a party to any sale.</strong> We don’t own, inspect, or deliver items, and we don’t handle, hold, or guarantee payments. Buyers and sellers pay each other directly, in person, using a method they agree on.</p>
      <p>We don’t verify listings, item condition, or the honesty of other students beyond confirming their school email. Use your judgment and inspect items before you pay.</p>
    </LegalSection>

    <LegalSection title="3. Listing items">
      <LegalList items={[
        "Only list items you own and have the right to sell.",
        "Describe items honestly, with real photos of the actual item, an accurate condition, and the price you’ll actually accept.",
        "Mark items correctly and remove listings that are no longer available.",
        <>Don’t list prohibited items: weapons; alcohol; tobacco and vapes; drugs, prescriptions, and drug paraphernalia; food; counterfeit or replica goods; stolen goods; recalled or unsafe items; adult content; or anything illegal to sell or own.</>,
      ]} />
    </LegalSection>

    <LegalSection title="4. Offers, deals, and handoffs">
      <LegalList items={[
        "An offer, counteroffer, or Buy now request is a request to the seller, not a completed purchase. A deal starts when the seller accepts.",
        "Whoever’s turn it is has 24 hours to respond to a request or offer, or it expires.",
        "Meetups can be scheduled up to 7 days ahead. While a deal is pending, the item is held for that buyer. If the handoff isn’t confirmed within 72 hours of the seller accepting, or within 2 hours after the agreed meetup if that’s later, the deal ends and the item becomes available again. A meetup can be rescheduled to a later time once.",
        "Other buyers can join a backup queue. If a deal falls through, the first eligible backup buyer is offered the item.",
        "An item is marked sold only when both buyer and seller confirm the handoff in Tanu. Only confirm a handoff that actually happened.",
        "If something goes wrong after a handoff is confirmed, report it in the deal. A Tanu moderator reviews disputed handoffs and decides how they’re settled; nothing is decided automatically.",
      ]} />
    </LegalSection>

    <LegalSection title="5. Meeting safely">
      <LegalList items={[
        "Meet in person at a public campus location, such as the meetup spots suggested in Tanu. Don’t meet in dorm rooms or private residences.",
        "Prefer daylight and busy places, and consider bringing a friend.",
        "Inspect the item before paying. Never pay in advance for an item you haven’t seen, and never share passwords or financial account details.",
        "If you feel unsafe, leave. In an emergency, call 911 or campus police.",
      ]} />
    </LegalSection>

    <LegalSection title="6. Community rules">
      <p>Don’t:</p>
      <LegalList items={[
        "Scam, mislead, or pressure other students, or take payment for items you don’t deliver.",
        "Harass, threaten, or discriminate against anyone, or send hateful, sexual, or violent content.",
        "Post spam, ads for outside businesses, or listings that aren’t real items for sale.",
        "Write fake or retaliatory reviews, or ask someone to change a review.",
        "Get around a block, suspension, or ban, for example with another account.",
        "Scrape Tanu, interfere with how it works, or try to access accounts or data that aren’t yours.",
      ]} />
    </LegalSection>

    <LegalSection title="7. Reports and moderation">
      <p>You can report listings, messages, users, and deals. Reports are reviewed by Tanu moderators; a report on its own never leads to an automatic penalty. If you break these Terms, we may remove content, cancel deals, limit features, suspend, or permanently ban your account, and we may keep records needed to protect the community. Where Tanu offers it, you can appeal a decision from your account.</p>
    </LegalSection>

    <LegalSection title="8. Your content">
      <p>You keep ownership of the photos, listings, messages, and reviews you post. You give Tanu a non-exclusive, royalty-free license to host, display, and process that content to run and improve Tanu, including showing your listings to students at your school. This license ends when your content is removed, except for copies kept in deal records, reports, and moderation evidence. Only post content you have the right to share.</p>
    </LegalSection>

    <LegalSection title="9. Deactivating your account">
      <p>You can deactivate your account at any time from your profile. Deactivation hides your profile and listings and withdraws you from open deals; it isn’t possible while a handoff is confirmed or under review. You can reactivate by logging in again, unless your account was suspended or banned. To ask for deletion, email <Email />.</p>
    </LegalSection>

    <LegalSection title="10. Disclaimers and limits">
      <p>Tanu is provided “as is” and “as available.” We don’t promise that it will always be available or error-free, and we aren’t responsible for the items students list, the conduct of buyers and sellers, or what happens at a handoff. To the fullest extent the law allows, Tanu won’t be liable for indirect or consequential damages, or for losses from transactions between students, and our total liability for any claim is limited to $50.</p>
      <p>You agree to be responsible for claims that arise from your listings, your transactions, or your breach of these Terms.</p>
    </LegalSection>

    <LegalSection title="11. Changes and governing law">
      <p>We may update these Terms. If we make important changes, we’ll update the date above and let you know through Tanu or by email before they take effect; continuing to use Tanu means you accept them. These Terms are governed by the laws of the State of Maryland.</p>
    </LegalSection>

    <LegalSection title="12. Contact">
      <p>Questions about these Terms, or something to report outside the app: <Email />.</p>
    </LegalSection>
  </LegalPage>;
}
