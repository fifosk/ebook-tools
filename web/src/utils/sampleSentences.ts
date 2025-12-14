import { resolveLanguageName } from '../constants/languageCodes';

const SAMPLE_SENTENCES: Record<string, string> = {
  af: "Hallo! Dit is 'n voorbeeldsin vir teks-na-spraak.",
  am: 'ሰላም! ይህ ለጽሑፍ ወደ ንግግር የሙከራ ንግግር ነው።',
  ar: 'مرحباً! هذه جملة نموذجية لتحويل النص إلى كلام.',
  be: 'Прывітанне! Гэта прыкладны сказ для сінтэзу маўлення.',
  bg: 'Здравейте! Това е примерна фраза за текст към реч.',
  bn: 'হ্যালো! এটি টেক্সট-টু-স্পিচের জন্য একটি নমুনা বাক্য।',
  bs: 'Zdravo! Ovo je primjer rečenice za pretvaranje teksta u govor.',
  ca: 'Hola! Aquesta és una frase de mostra per a text a veu.',
  cs: 'Ahoj! Toto je ukázková věta pro převod textu na řeč.',
  cy: 'Helo! Dyma frawddeg sampl ar gyfer testun-i-leferydd.',
  da: 'Hej! Dette er en eksempel­sætning til tekst-til-tale.',
  de: 'Hallo! Dies ist ein Beispielsatz für Text-zu-Sprache.',
  el: 'Γεια! Αυτή είναι μια δοκιμαστική πρόταση για μετατροπή κειμένου σε ομιλία.',
  en: 'Hello! This is a sample sentence for text-to-speech.',
  eo: 'Saluton! Ĉi tio estas ekzempla frazo por tekst-al-parolo.',
  es: '¡Hola! Esta es una frase de muestra para texto a voz.',
  et: 'Tere! See on näidislause teksti kõneks muutmiseks.',
  eu: 'Kaixo! Hau testutik ahotsera egiteko esaldi adibide bat da.',
  fa: 'سلام! این یک جملهٔ نمونه برای تبدیل متن به گفتار است.',
  fi: 'Hei! Tämä on esimerkkilause tekstistä puheeksi.',
  fo: 'Halló! Hetta er ein dømisetningur til tekst-til-talu.',
  fr: 'Bonjour ! Ceci est une phrase d’exemple pour la synthèse vocale.',
  ga: 'Dia duit! Seo abairt shamplach le haghaidh téacs-go-caint.',
  gd: 'Halò! Seo seantans sampaill airson teacsa-gu-cainnt.',
  gl: 'Ola! Esta é unha frase de mostra para texto a voz.',
  gu: 'નમસ્તે! આ ટેક્સ્ટ-ટુ-સ્પીચ માટેનું નમૂના વાક્ય છે.',
  ha: 'Sannu! Wannan jumla ce ta misali don rubutu-zuwa-magana.',
  he: 'שלום! זהו משפט לדוגמה להמרת טקסט לדיבור.',
  hi: 'नमस्ते! यह टेक्स्ट-टू-स्पीच के लिए एक नमूना वाक्य है।',
  hr: 'Pozdrav! Ovo je primjer rečenice za pretvorbu teksta u govor.',
  hu: 'Szia! Ez egy mintamondat a szövegfelolvasáshoz.',
  hy: 'Բարեւ։ Սա տեքստից խոսքի համար օրինակ նախադասություն է։',
  id: 'Halo! Ini adalah kalimat contoh untuk teks ke suara.',
  is: 'Hæ! Þetta er dæmisetning fyrir texta í tal.',
  it: 'Ciao! Questa è una frase di esempio per la sintesi vocale.',
  ja: 'こんにちは！これはテキスト読み上げのサンプル文です。',
  jw: 'Halo! Iki ukara conto kanggo text-to-speech.',
  ka: 'გამარჯობა! ეს არის მაგალითი წინადადება ტექსტიდან მეტყველებისთვის.',
  kk: 'Сәлем! Бұл мәтінді сөйлеуге айналдыруға арналған үлгі сөйлем.',
  km: 'សួស្តី! នេះជាប្រយោគគំរូសម្រាប់អត្ថបទទៅសំឡេង។',
  kn: 'ನಮಸ್ಕಾರ! ಇದು ಪಠ್ಯದಿಂದ ಭಾಷಣಕ್ಕೆ ಮಾದರಿ ವಾಕ್ಯ.',
  ko: '안녕하세요! 이것은 텍스트 음성 변환을 위한 예문입니다.',
  ky: 'Салам! Бул текстти үнгө айландыруу үчүн үлгү сүйлөм.',
  la: 'Salve! Haec est sententia exemplaris ad textum in vocem.',
  lb: 'Moien! Dëst ass e Beispillsaz fir Text-zu-Sprooch.',
  lt: 'Sveiki! Tai pavyzdinis sakinys teksto pavertimui į kalbą.',
  lv: 'Sveiki! Šis ir parauga teikums teksta pārvēršanai runā.',
  mk: 'Здраво! Ова е примерна реченица за текст во говор.',
  ml: 'ഹലോ! ഇത് ടെക്സ്റ്റ്-ടു-സ്പീച്ചിനുള്ള ഒരു ഉദാഹരണ വാക്യം ആണ്.',
  mn: 'Сайн байна уу! Энэ нь текстийг яриа болгох жишээ өгүүлбэр юм.',
  mr: 'नमस्कार! हे टेक्स्ट-टू-स्पीचसाठी एक नमुना वाक्य आहे.',
  ms: 'Hai! Ini ialah ayat contoh untuk teks-ke-pertuturan.',
  mt: 'Bongu! Din hija sentenza ta’ eżempju għat-test għal diskors.',
  my: 'မင်္ဂလာပါ။ ဒီဟာက စာသားမှ အသံအတွက် နမူနာစာကြောင်းပါ။',
  ne: 'नमस्ते! यो टेक्स्ट-टु-स्पिचका लागि नमूना वाक्य हो।',
  nl: 'Hallo! Dit is een voorbeeldzin voor tekst-naar-spraak.',
  no: 'Hei! Dette er en eksempelsetning for tekst-til-tale.',
  pa: 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਇਹ ਟੈਕਸਟ-ਟੂ-ਸਪੀਚ ਲਈ ਇੱਕ ਨਮੂਨਾ ਵਾਕ ਹੈ।',
  pl: 'Cześć! To jest przykładowe zdanie do syntezy mowy.',
  ps: 'سلام! دا د متن-تر-وينا لپاره یوه بېلګه جمله ده.',
  pt: 'Olá! Esta é uma frase de exemplo para texto para fala.',
  'pt-br': 'Olá! Esta é uma frase de exemplo para texto para fala.',
  ro: 'Salut! Aceasta este o propoziție de exemplu pentru text-în-vorbire.',
  rom: 'Sastipe! Akava si jekh misalo fraza vaš text-to-speech.',
  ru: 'Здравствуйте! Это пример предложения для синтеза речи.',
  sco: 'Hallo! This is a sample sentence for text-ta-speech.',
  si: 'හෙලෝ! මෙය පෙළ-සිට කථනයට සදහා නියැදි වාක්‍යයකි.',
  sk: 'Ahoj! Toto je ukážková veta pre prevod textu na reč.',
  sl: 'Živjo! To je vzorčni stavek za pretvorbo besedila v govor.',
  sq: 'Përshëndetje! Kjo është një fjali shembull për tekst në të folur.',
  sr: 'Zdravo! Ovo je primer rečenice za tekst u govor.',
  su: 'Halo! Ieu kalimah conto pikeun téks-ka-ucapan.',
  sv: 'Hej! Det här är en exempelsats för text-till-tal.',
  sw: 'Habari! Hili ni sentensi ya mfano kwa maandishi-kwa-sauti.',
  ta: 'வணக்கம்! இது உரையிலிருந்து பேச்சிற்கு ஒரு மாதிரி வாக்கியம்.',
  te: 'నమస్తే! ఇది టెక్స్ట్-టు-స్పీచ్ కోసం ఒక నమూనా వాక్యం.',
  tg: 'Салом! Ин ҷумлаи намунавӣ барои матн‑ба‑овоз аст.',
  th: 'สวัสดี! นี่คือประโยคตัวอย่างสำหรับแปลงข้อความเป็นเสียงพูด',
  tk: 'Salam! Bu tekstden sese öwürmek üçin nusga sözlem.',
  tl: 'Kumusta! Ito ay halimbawang pangungusap para sa text-to-speech.',
  tr: 'Merhaba! Bu, metinden konuşmaya için örnek bir cümledir.',
  uk: 'Привіт! Це приклад речення для синтезу мовлення.',
  ur: 'سلام! یہ متن سے آواز کے لیے ایک نمونہ جملہ ہے۔',
  uz: 'Salom! Bu matndan nutqqa uchun namunaviy gap.',
  vi: 'Xin chào! Đây là câu mẫu cho chuyển văn bản thành giọng nói.',
  xh: 'Molo! Le ngumhlathi wesampuli woguqulelo lombhalo uye kwintetho.',
  yo: 'Báwo! Èyí ni gbolóhùn àpẹẹrẹ fún ìyípadà ìkọ̀wé sí ohùn.',
  zu: 'Sawubona! Lona umusho wesampula wokuguqula umbhalo ube yinkulumo.',
  'zh-cn': '你好！这是用于文本转语音的示例句子。',
  'zh-tw': '你好！這是用於文字轉語音的示例句子。'
};

export function sampleSentenceFor(languageCode: string, fallbackLabel?: string): string {
  const raw = languageCode.trim();
  if (!raw) {
    return SAMPLE_SENTENCES.en;
  }

  const canonical = raw.replace(/_/g, '-').toLowerCase();
  const direct = SAMPLE_SENTENCES[canonical];
  if (direct) {
    return direct;
  }

  const base = canonical.split('-')[0];
  const baseSentence = base && base !== canonical ? SAMPLE_SENTENCES[base] : undefined;
  if (baseSentence) {
    return baseSentence;
  }

  const resolvedName = resolveLanguageName(raw) ?? (fallbackLabel ?? '').trim();
  if (!resolvedName) {
    return SAMPLE_SENTENCES.en;
  }
  return `Sample narration for ${resolvedName}.`;
}

