import type { Metadata } from "next";
import Link from "next/link";

import { LegalList, LegalPage, LegalSection } from "@/components/legal-page";
import { SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy Policy", description: "What Tanu collects, why, and the choices you have." };

const Email = () => <a href={`mailto:${SUPPORT_EMAIL}`} className="font-semibold underline decoration-kraft decoration-2 underline-offset-4">{SUPPORT_EMAIL}</a>;

export default function PrivacyPage() {
  return <LegalPage
    title="Privacy Policy"
    updated="November 13, 2026"
    intro={<>
      <p>Tanu is a marketplace where verified students buy and sell items with other students at their school. This policy explains what we collect, why, who can see it, and the choices you have. “Tanu,” “we,” and “us” mean the team that operates tanu.one.</p>
      <p>Tanu is independent and is not affiliated with or endorsed by any university.</p>
    </>}
  >
    <LegalSection title="1. What we collect">
      <p><strong>Information you give us:</strong></p>
      <LegalList items={[
        <>Your account: first and last name, a username, your school email address, and a password (stored only in scrambled, one-way form). Your school is set from your verified email.</>,
        <>Optional profile details, such as a short description and an Instagram handle.</>,
        <>Listings: photos, titles, descriptions, prices, condition, size, brand, and category.</>,
        <>Activity in the marketplace: messages, offers and counteroffers, deals, meetup preferences and availability, proposed and confirmed meetup times and spots, handoff confirmations, and reviews.</>,
        <>Things you save: bookmarks, saved searches, follows, and blocks.</>,
        <>Reports you make, appeals, and anything you send to support.</>,
      ]} />
      <p><strong>Information created as you use Tanu:</strong> the history of each deal (who did what and when), notifications we send you, and, when something is reported, copies of the reported content kept as evidence for moderators.</p>
      <p><strong>Technical information:</strong> a session cookie that keeps you signed in and a security cookie that protects forms. We don’t use advertising or cross-site tracking cookies. Our hosting providers keep standard server logs, which can include IP addresses, for a limited time to run and secure the service.</p>
    </LegalSection>

    <LegalSection title="2. How we use it">
      <LegalList items={[
        "To verify that you’re a student at a participating school and keep the marketplace students-only.",
        "To run the marketplace: show listings to students at your school, deliver messages, and support offers, deals, meetups, and handoff confirmation.",
        "To send account and activity emails, such as verification links, password resets, and notifications about your own deals and messages. We don’t send marketing email.",
        "To keep people safe: review reports, investigate scams and prohibited items, enforce our Terms, and act on violations.",
        "To fix problems and keep Tanu secure and reliable.",
      ]} />
      <p>We do not sell your personal information, and we don’t use it for advertising.</p>
    </LegalSection>

    <LegalSection title="3. Who can see what">
      <LegalList items={[
        "Other students can see your username, first name, school, profile details you add, your listings, and reviews about you. Your last name and email address are not shown to other students.",
        "Signed-in students can see who follows you and who you follow.",
        "Messages are visible to the people in the conversation. Deal and meetup details are visible to the buyer and seller in that deal.",
        "Tanu moderators can see reported content and the records needed to review a report, such as the listing, the conversation, or the deal history involved. Access to evidence is logged.",
        "If you block someone, neither of you can message or make deals with the other. They aren’t told that you blocked them.",
      ]} />
    </LegalSection>

    <LegalSection title="4. Services that help run Tanu">
      <p>We use trusted providers to host and operate Tanu. They process information only to provide their service to us:</p>
      <LegalList items={[
        "Vercel (website hosting) and Heroku (application servers).",
        "Supabase (database hosting).",
        "Cloudflare (domain and security services, photo and file storage, and forwarding email sent to our addresses).",
        "Postmark (delivering account and notification emails).",
        "Sentry (error monitoring, configured to exclude personal information).",
      ]} />
      <p>We may also share information if the law requires it, to protect the safety of students or the public, or as part of a merger or sale of Tanu, in which case this policy would continue to apply to your information.</p>
    </LegalSection>

    <LegalSection title="5. How long we keep it">
      <p>We keep your information while your account exists. If you deactivate your account, your profile and listings are hidden, and you can come back by logging in again.</p>
      <p>Some records are kept even after an account is deactivated or deleted, because they protect other students and keep the marketplace fair: deal histories, reviews, reports, moderation decisions, and evidence. If an account is banned, we keep its email address so it can’t be used to sign up again.</p>
    </LegalSection>

    <LegalSection title="6. Your choices">
      <LegalList items={[
        <>Edit your profile and listings at any time, and manage your saved searches from your <Link href="/profile" className="font-semibold underline decoration-kraft decoration-2 underline-offset-4">profile</Link>.</>,
        "Deactivate your account from your profile settings.",
        <>Ask for a copy of your information, a correction, or deletion of your account by emailing <Email />. We’ll delete or de-identify what we can, apart from the records described in section 5.</>,
      ]} />
    </LegalSection>

    <LegalSection title="7. Security">
      <p>We protect your information with measures such as encrypted connections, scrambled password storage, restricted staff access, and private storage for moderation evidence. No service can promise perfect security, so please use a unique password and tell us right away if you think your account has been compromised.</p>
    </LegalSection>

    <LegalSection title="8. Age">
      <p>Tanu is for students who are 18 or older. We don’t knowingly collect information from anyone younger. If you believe someone under 18 has an account, contact us and we’ll remove it.</p>
    </LegalSection>

    <LegalSection title="9. Changes to this policy">
      <p>If we make important changes, we’ll update the date above and let you know through Tanu or by email before they take effect.</p>
    </LegalSection>

    <LegalSection title="10. Contact">
      <p>Questions or requests about your privacy: <Email />.</p>
    </LegalSection>
  </LegalPage>;
}
