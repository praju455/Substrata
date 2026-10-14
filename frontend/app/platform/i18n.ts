import { useSyncExternalStore } from "react";

export const locales = ["en", "hi"] as const;

export type Locale = (typeof locales)[number];

const hindi = {
  "The assessment is missing its original graph snapshot.": "आकलन का मूल ग्राफ़ स्नैपशॉट उपलब्ध नहीं है।",
  Evidence: "साक्ष्य",
  "Evidence and supplier review": "साक्ष्य और आपूर्तिकर्ता समीक्षा",
  "Store sourced passages, retrieve evidence, and propose relationships for review.": "स्रोत सहित अंश सहेजें, साक्ष्य खोजें और समीक्षा के लिए संबंध प्रस्तावित करें।",
  "Add an evidence document": "साक्ष्य दस्तावेज़ जोड़ें",
  "Document ID": "दस्तावेज़ आईडी",
  "Source URI": "स्रोत का पता",
  "Source kind": "स्रोत का प्रकार",
  "Source note": "स्रोत टिप्पणी",
  "Document text": "दस्तावेज़ का पाठ",
  "Save document": "दस्तावेज़ सहेजें",
  "stored documents": "सहेजे गए दस्तावेज़",
  "Index documents": "दस्तावेज़ अनुक्रमित करें",
  "Evidence query": "साक्ष्य खोज",
  "Search passages": "अंश खोजें",
  "Discover cited links": "संदर्भ सहित संबंध खोजें",
  "Similarity scores measure retrieval relevance, not relationship confidence. Discovered links remain inferred until supplier review.": "समानता स्कोर खोज की प्रासंगिकता बताता है, संबंध का विश्वास स्तर नहीं। आपूर्तिकर्ता की समीक्षा तक खोजे गए संबंध अनुमानित रहते हैं।",
  "No indexed passages found. Index documents before searching.": "कोई अनुक्रमित अंश नहीं मिला। खोजने से पहले दस्तावेज़ अनुक्रमित करें।",
  Relevance: "प्रासंगिकता",
  "Request supplier confirmation": "आपूर्तिकर्ता पुष्टि का अनुरोध करें",
  "Relationship to review": "समीक्षा हेतु संबंध",
  "Local preview only. No supplier email is sent.": "केवल स्थानीय पूर्वावलोकन। आपूर्तिकर्ता को ईमेल नहीं भेजा जाता।",
  "Supplier email": "आपूर्तिकर्ता ईमेल",
  "Create confirmation request": "पुष्टि अनुरोध बनाएँ",
  "Open local supplier preview": "स्थानीय आपूर्तिकर्ता पूर्वावलोकन खोलें",
  "Background tasks": "पृष्ठभूमि कार्य",
  "Tasks run when a worker is active or when you run the next task here. Refresh to see progress.": "वर्कर सक्रिय होने पर या यहाँ अगला कार्य चलाने पर कार्य चलते हैं। प्रगति देखने के लिए रीफ़्रेश करें।",
  "Queue risk review": "जोखिम समीक्षा कतार में जोड़ें",
  "Queue event feed check": "इवेंट फ़ीड जाँच कतार में जोड़ें",
  "Run next queued task": "कतार का अगला कार्य चलाएँ",
  "No background tasks yet.": "अभी कोई पृष्ठभूमि कार्य नहीं है।",
  Attempt: "प्रयास",
  "Next eligible attempt": "अगले प्रयास का समय",
  "Completed review steps": "पूरे हुए समीक्षा चरण",
  event_poll: "इवेंट फ़ीड जाँच",
  assessment: "आकलन",
  agent_task: "एजेंट कार्य",
  agent_plan: "एजेंट समीक्षा योजना",
  "cascade_caller.assessment": "कैस्केड आकलन",
  "compliance_audit.verification": "ऑडिट सत्यापन",
  Language: "भाषा",
  "Skip to workspace": "कार्यक्षेत्र पर जाएँ",
  "Platform sections": "प्लेटफ़ॉर्म अनुभाग",
  Onboarding: "शुरुआत",
  Imports: "आयात",
  Network: "नेटवर्क",
  Approvals: "अनुमोदन",
  "Tenant workspace": "टेनेंट कार्यक्षेत्र",
  "SUPPLY NETWORK INTELLIGENCE": "आपूर्ति नेटवर्क जानकारी",
  "Your supply network": "आपका आपूर्ति नेटवर्क",
  "Trace your dependencies, measure production runway, and review the next action.":
    "अपनी निर्भरताएँ देखें, उत्पादन की उपलब्ध अवधि मापें और अगली कार्रवाई की समीक्षा करें।",
  "Refresh workspace": "कार्यक्षेत्र रीफ़्रेश करें",
  "Sign out": "साइन आउट",
  "Sign in with your organisation": "अपने संगठन से साइन इन करें",
  "Your organisation determines the network and approvals you can access.":
    "आपका संगठन तय करता है कि आप किस नेटवर्क और अनुमोदन तक पहुँच सकते हैं।",
  "Continue with SSO": "SSO से जारी रखें",
  "Local development access": "स्थानीय विकास पहुँच",
  Import: "आयात",
  "Development access token": "विकास एक्सेस टोकन",
  "Open local workspace": "स्थानीय कार्यक्षेत्र खोलें",
  "Start the platform API to connect this workspace.":
    "इस कार्यक्षेत्र से जुड़ने के लिए प्लेटफ़ॉर्म API शुरू करें।",
  "Loading your organisation…": "आपका संगठन लोड हो रहा है…",
  "GET STARTED": "शुरू करें",
  "Set up your organisation": "अपना संगठन सेट करें",
  "Organisation name": "संगठन का नाम",
  "Create organisation": "संगठन बनाएँ",
  "Organisation created": "संगठन बनाया गया",
  "Network data loaded": "नेटवर्क डेटा लोड हुआ",
  "Import your network data": "अपना नेटवर्क डेटा आयात करें",
  "Approval policy configured": "अनुमोदन नीति कॉन्फ़िगर हुई",
  "Set an approval policy": "अनुमोदन नीति सेट करें",
  "Assess a disruption and review an action":
    "बाधा का आकलन करें और कार्रवाई की समीक्षा करें",
  "Explore synthetic industry examples": "काल्पनिक उद्योग उदाहरण देखें",
  "Invented records for demonstration. These are not customer or supplier facts.":
    "ये प्रदर्शन के लिए बनाए गए काल्पनिक रिकॉर्ड हैं, ग्राहक या आपूर्तिकर्ता के तथ्य नहीं।",
  Industry: "उद्योग",
  "Automotive electronics": "ऑटोमोटिव इलेक्ट्रॉनिक्स",
  Pharma: "औषधि उद्योग",
  Food: "खाद्य उद्योग",
  "Load synthetic example": "काल्पनिक उदाहरण लोड करें",
  "Data quality": "डेटा गुणवत्ता",
  "Graph revision": "ग्राफ संशोधन",
  "Missing inventory inputs": "गुम इन्वेंटरी जानकारी",
  "Inferred links": "अनुमानित संबंध",
  "Audit chain": "ऑडिट शृंखला",
  "Check required": "जाँच आवश्यक",
  Verified: "सत्यापित",
  "Data imports": "डेटा आयात",
  "Preview CSV or Excel columns, validate the mapping, then apply a reviewed import.":
    "CSV या Excel कॉलम का पूर्वावलोकन करें, मैपिंग जाँचें और समीक्षा के बाद आयात लागू करें।",
  Table: "तालिका",
  Entities: "इकाइयाँ",
  Inventory: "इन्वेंटरी",
  Links: "संबंध",
  "Purchase orders": "खरीद आदेश",
  "BOM items": "BOM आइटम",
  "Quantity unit": "मात्रा की इकाई",
  File: "फ़ाइल",
  "Preview columns": "कॉलम का पूर्वावलोकन",
  "Not mapped": "मैप नहीं किया गया",
  "Validate and stage": "जाँचें और तैयार रखें",
  "Apply import": "आयात लागू करें",
  "Rollback with reason": "कारण सहित वापस लें",
  "Resolve ambiguous identities": "अस्पष्ट पहचान सुलझाएँ",
  "Keep each incoming entity separate": "हर नई इकाई को अलग रखें",
  "Graph explorer": "ग्राफ खोज",
  Revision: "संशोधन",
  Search: "खोजें",
  "Name or identifier": "नाम या पहचानकर्ता",
  "Relationship status": "संबंध स्थिति",
  "All statuses": "सभी स्थितियाँ",
  "Dependency depth": "निर्भरता की गहराई",
  "As-of date": "इस तारीख तक",
  "View history": "इतिहास देखें",
  "Latest revision": "नवीनतम संशोधन",
  "Inspect a link": "संबंध देखें",
  "Choose a relationship": "संबंध चुनें",
  "Evidence support": "साक्ष्य समर्थन",
  uncalibrated: "अंशांकित नहीं",
  "Scenario runner": "परिदृश्य चलाएँ",
  "Assess a full source interruption using the selected immutable graph revision.":
    "चुने गए अपरिवर्तनीय ग्राफ संशोधन से स्रोत की पूर्ण बाधा का आकलन करें।",
  "Affected source": "प्रभावित स्रोत",
  "Choose an entity": "इकाई चुनें",
  Severity: "गंभीरता",
  "Traversal depth": "खोज की गहराई",
  "Calculate runway": "उपलब्ध अवधि की गणना करें",
  "Traversal was truncated. Mitigations are blocked until assessment is complete.":
    "खोज सीमित कर दी गई। आकलन पूरा होने तक जोखिम-निवारण रोका गया है।",
  "Stock cover": "स्टॉक उपलब्धता",
  days: "दिन",
  Requalification: "पुनः-योग्यता",
  "Exposure range": "जोखिम सीमा",
  "Approval policy": "अनुमोदन नीति",
  "Limits are explicit organisation assumptions. A separate approver is required by default.":
    "सीमाएँ संगठन की स्पष्ट मान्यताएँ हैं। सामान्यतः अलग अनुमोदक आवश्यक है।",
  Currency: "मुद्रा",
  "Maximum spend": "अधिकतम खर्च",
  "Automatic approval limit": "स्वचालित अनुमोदन सीमा",
  "Organisation spending limit": "संगठन की खर्च सीमा",
  "Organisation automatic approval limit": "संगठन की स्वचालित अनुमोदन सीमा",
  "Organisation approval SLA": "संगठन की अनुमोदन समय-सीमा",
  "Save policy": "नीति सहेजें",
  "Approvals inbox": "अनुमोदन इनबॉक्स",
  "Decision or rollback reason": "निर्णय या वापस लेने का कारण",
  "Explain the evidence and decision": "साक्ष्य और निर्णय का कारण बताएँ",
  "Draft a mitigation from a sourced quote":
    "स्रोत-आधारित कोटेशन से जोखिम-निवारण प्रस्ताव बनाएँ",
  "Quote source and rationale": "कोटेशन का स्रोत और कारण",
  Cost: "लागत",
  "Duration in days": "अवधि (दिनों में)",
  "Create approval draft": "अनुमोदन प्रस्ताव बनाएँ",
  Approve: "अनुमोदित करें",
  Reject: "अस्वीकार करें",
  "Record dry-run preview": "ड्राई-रन पूर्वावलोकन दर्ज करें",
  "Assess a disruption, then draft a sourced mitigation to begin review.":
    "समीक्षा शुरू करने के लिए पहले बाधा का आकलन करें, फिर स्रोत-आधारित जोखिम-निवारण प्रस्ताव बनाएँ।",
  "Acknowledgement reason": "स्वीकृति का कारण",
  "Acknowledge alert": "अलर्ट स्वीकार करें",
  "Unmatched event": "बिना मिलान की घटना",
  "Possible name-only sanctions or export-control candidate. Mapping the entity does not determine sanctions status, export authorization, or clearance.":
    "नाम-आधारित प्रतिबंध या निर्यात-नियंत्रण का संभावित उम्मीदवार। इकाई मैप करने से प्रतिबंध स्थिति, निर्यात अनुमति या मंज़ूरी तय नहीं होती।",
  "Event needs entity review": "घटना की इकाई की समीक्षा आवश्यक है",
  "This product uses the International Trade Administration’s Data API but is not endorsed or certified by the International Trade Administration.":
    "यह उत्पाद International Trade Administration के Data API का उपयोग करता है, पर उस संस्था से समर्थित या प्रमाणित नहीं है।",
  "Match to entity": "इकाई से मिलान करें",
  "Select an entity": "इकाई चुनें",
  "Resolution reason": "सुलझाने का कारण",
  "Map entity for review": "समीक्षा के लिए इकाई मैप करें",
  "Map event to entity": "घटना को इकाई से मैप करें",
  "No alerts or approval notifications yet.":
    "अभी कोई अलर्ट या अनुमोदन सूचना नहीं है।",
  "Alert centre": "अलर्ट केंद्र",
  "Reports and audit": "रिपोर्ट और ऑडिट",
  "Audit chain verified": "ऑडिट शृंखला सत्यापित",
  "Audit verification requires attention":
    "ऑडिट सत्यापन पर ध्यान देना आवश्यक है",
  records: "रिकॉर्ड",
  "Print or save PDF": "प्रिंट करें या PDF सहेजें",
  "Export audit JSON": "ऑडिट JSON निर्यात करें",
  "Export CSV": "CSV निर्यात करें",
  "Chain head:": "शृंखला शीर्ष:",
  "Audit chain head:": "ऑडिट शृंखला शीर्ष:",
  "Saved. Your workspace is up to date.":
    "सहेजा गया। आपका कार्यक्षेत्र नवीनतम है।",
  "The operation failed.": "कार्रवाई विफल हुई।",
  "Platform is unavailable.": "प्लेटफ़ॉर्म उपलब्ध नहीं है।",
  "Sign-in state did not match. Start sign-in again.":
    "साइन-इन स्थिति मेल नहीं खाती। फिर से साइन इन करें।",
  "Check the entered values and permissions.": "दर्ज मान और अनुमतियाँ जाँचें।",
  "Export failed.": "निर्यात विफल हुआ।",
  "Load a graph snapshot before exporting a report.":
    "रिपोर्ट निर्यात करने से पहले ग्राफ स्नैपशॉट लोड करें।",
  "Allow the report window to open, then try again.":
    "रिपोर्ट विंडो खोलने की अनुमति दें और फिर कोशिश करें।",
  "Choose a file smaller than 3 MB.": "3 MB से छोटी फ़ाइल चुनें।",
  "Supply risk assessment": "आपूर्ति जोखिम आकलन",
  "Report generated:": "रिपोर्ट बनाई गई:",
  "Revision recorded:": "संशोधन दर्ज हुआ:",
  "Entities / links:": "इकाइयाँ / संबंध:",
  "Assessment created:": "आकलन बनाया गया:",
  "No saved assessment": "कोई सहेजा हुआ आकलन नहीं",
  "Assessment as of:": "इस तारीख तक आकलन:",
  "Not verified": "सत्यापित नहीं",
  "Graph coverage": "ग्राफ कवरेज",
  confirmed: "पुष्ट",
  inferred: "अनुमानित",
  declared: "घोषित",
  rejected: "अस्वीकृत",
  expired: "समाप्त",
  "declared links": "घोषित संबंध",
  "Affected materials and plants": "प्रभावित सामग्री और संयंत्र",
  Material: "सामग्री",
  Plant: "संयंत्र",
  Cover: "उपलब्धता",
  "Requalification days": "पुनः-योग्यता दिन",
  Status: "स्थिति",
  "No saved assessment is available for this graph revision.":
    "इस ग्राफ संशोधन के लिए कोई सहेजा हुआ आकलन उपलब्ध नहीं है।",
  "Uncertainty and method": "अनिश्चितता और विधि",
  "This report reflects the selected graph revision and any saved deterministic assessment shown above. Inferred relationships and exposure ranges carry uncertainty; review their source evidence and provenance before acting. The report is informational and does not authorize procurement or legal clearance.":
    "यह रिपोर्ट चुने गए ग्राफ संशोधन और ऊपर दिखाए गए सहेजे हुए नियतात्मक आकलन पर आधारित है। अनुमानित संबंधों और जोखिम सीमाओं में अनिश्चितता है; कार्रवाई से पहले स्रोत-साक्ष्य और उद्गम देखें। यह रिपोर्ट केवल जानकारी देती है और खरीद या कानूनी मंज़ूरी की अनुमति नहीं देती।",
  "Graph snapshot SHA-256:": "ग्राफ स्नैपशॉट SHA-256:",
  Supplier: "आपूर्तिकर्ता",
  Site: "स्थान",
  Product: "उत्पाद",
  Region: "क्षेत्र",
  pending: "लंबित",
  blocked: "रोका गया",
  approved: "अनुमोदित",
  open: "खुला",
  staged: "तैयार",
  applied: "लागू",
  rolled_back: "वापस लिया गया",
  complete: "पूरा",
  incomplete: "अधूरा",
  needs_review: "समीक्षा आवश्यक",
  succeeded: "सफल",
  failed: "विफल",
  invalid: "अमान्य",
  rows: "पंक्तियाँ",
  viewer: "दर्शक",
  analyst: "विश्लेषक",
  approver: "अनुमोदक",
  admin: "व्यवस्थापक",
  synthetic: "काल्पनिक",
  uploaded: "अपलोड किया गया",
  connector: "कनेक्टर",
  public: "सार्वजनिक",
  supplier: "आपूर्तिकर्ता",
  assumption: "मान्यता",
  SUPPLIES: "आपूर्ति करता है",
  DEPENDS_ON: "निर्भर है",
  USED_IN: "इसमें उपयोग होता है",
  OWNED_BY: "स्वामित्व में है",
  LOCATED_IN: "इसमें स्थित है",
  supplier_confirmation: "आपूर्तिकर्ता पुष्टि",
  "This link is missing its confirmation token.":
    "इस लिंक में पुष्टि टोकन नहीं है।",
  "The link is unavailable or expired.":
    "यह लिंक उपलब्ध नहीं है या समाप्त हो चुका है।",
  "Your response could not be recorded.": "आपका उत्तर दर्ज नहीं किया जा सका।",
  "Thank you. Your response has been recorded with its rationale.":
    "धन्यवाद। आपका उत्तर और उसका कारण दर्ज कर लिया गया है।",
  "The request failed.": "अनुरोध विफल हुआ।",
  "SUBSTRATA · SUPPLIER CONFIRMATION": "SUBSTRATA · आपूर्तिकर्ता पुष्टि",
  "Review this relationship": "इस संबंध की समीक्षा करें",
  "This is a relationship claim for your review. It does not authorise a purchase or operational change.":
    "यह संबंध का दावा आपकी समीक्षा के लिए है। इससे खरीद या परिचालन बदलाव की अनुमति नहीं मिलती।",
  "Link expires": "लिंक की समय-सीमा",
  "Your name or supplier reference": "आपका नाम या आपूर्तिकर्ता संदर्भ",
  Reason: "कारण",
  "Confirm relationship": "संबंध की पुष्टि करें",
  "Reject relationship": "संबंध अस्वीकार करें",
} satisfies Record<string, string>;

export type CopyKey = keyof typeof hindi;
export const copyKeys = Object.keys(hindi) as CopyKey[];

export function isLocale(value: string | null): value is Locale {
  return value !== null && locales.some((locale) => locale === value);
}

export function translate(locale: Locale, key: CopyKey): string {
  return locale === "hi" ? hindi[key] : key;
}

export function localizeMessage(locale: Locale, value: string): string {
  return locale === "hi" && copyKeys.includes(value as CopyKey)
    ? hindi[value as CopyKey]
    : value;
}

export function localeTag(locale: Locale): string {
  return locale === "hi" ? "hi-IN" : "en-US";
}

let memoryLocale: Locale | null = null;
const localeListeners = new Set<() => void>();

function readLocale(): Locale {
  if (typeof window === "undefined") return "en";
  if (memoryLocale) return memoryLocale;
  try {
    const saved = window.localStorage.getItem("substrata-locale");
    if (isLocale(saved)) return saved;
  } catch {
    // Use browser language when persistent storage is unavailable.
  }
  const browser = window.navigator.language.split("-")[0] || "en";
  return isLocale(browser) ? browser : "en";
}

function subscribeLocale(listener: () => void): () => void {
  localeListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    localeListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function serverLocale(): Locale {
  return "en";
}

export function chooseLocale(locale: Locale): void {
  memoryLocale = locale;
  try {
    window.localStorage.setItem("substrata-locale", locale);
  } catch {
    // The selected language still applies for this browser session.
  }
  document.documentElement.lang = localeTag(locale);
  localeListeners.forEach((listener) => listener());
}

export function useLocale(): [Locale, (locale: Locale) => void] {
  const locale = useSyncExternalStore(
    subscribeLocale,
    readLocale,
    serverLocale,
  );
  return [locale, chooseLocale];
}
