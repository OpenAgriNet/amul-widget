import type { WidgetLocale } from "@openagrinet/amul-widget-contracts"

type WidgetCopy = {
  language: string
  welcome: string
  placeholder: string
  unavailable: string
  retry: string
  close: string
  send: string
  questions: string[]
}

export const languageLabels: Record<WidgetLocale, string> = {
  en: "English",
  hi: "हिन्दी",
  gu: "ગુજરાતી",
}

export const widgetCopy: Record<WidgetLocale, WidgetCopy> = {
  en: {
    language: "Choose language",
    welcome: "Namaste! Ask me for practical advice about farming and animal care.",
    placeholder: "Ask me anything…",
    unavailable: "The advisory service is temporarily unavailable.",
    retry: "Try again",
    close: "Close Amul AI",
    send: "Send question",
    questions: [
      "How can I improve milk production?",
      "What should I feed my cattle?",
      "How can mastitis be prevented?",
      "How do I protect crops from pests?",
      "How should I prepare for heavy rain?",
    ],
  },
  hi: {
    language: "भाषा चुनें",
    welcome: "नमस्ते! खेती और पशुपालन पर व्यावहारिक सलाह के लिए मुझसे पूछें।",
    placeholder: "मुझसे कुछ भी पूछें…",
    unavailable: "सलाह सेवा अभी उपलब्ध नहीं है।",
    retry: "फिर कोशिश करें",
    close: "Amul AI बंद करें",
    send: "सवाल भेजें",
    questions: [
      "दूध उत्पादन कैसे बढ़ाया जा सकता है?",
      "मुझे अपने पशुओं को क्या खिलाना चाहिए?",
      "मास्टाइटिस से कैसे बचाव करें?",
      "फसल को कीटों से कैसे बचाएं?",
      "भारी बारिश की तैयारी कैसे करें?",
    ],
  },
  gu: {
    language: "ભાષા પસંદ કરો",
    welcome: "નમસ્તે! ખેતી અને પશુપાલન વિશે વ્યવહારુ સલાહ માટે મને પૂછો.",
    placeholder: "મને કંઈપણ પૂછો…",
    unavailable: "સલાહ સેવા હાલમાં ઉપલબ્ધ નથી.",
    retry: "ફરી પ્રયાસ કરો",
    close: "Amul AI બંધ કરો",
    send: "પ્રશ્ન મોકલો",
    questions: [
      "દૂધ ઉત્પાદન કેવી રીતે વધારી શકાય?",
      "મારા પશુઓને શું ખવડાવવું જોઈએ?",
      "મસ્તાઇટિસથી કેવી રીતે બચી શકાય?",
      "પાકને જીવાતોથી કેવી રીતે બચાવવો?",
      "ભારે વરસાદ માટે કેવી તૈયારી કરવી?",
    ],
  },
}
