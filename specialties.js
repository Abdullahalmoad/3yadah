// ========================================
// specialties.js — التخصصات الطبية العراقية
// نظام عيادة v7.0 — عبدالله الموعد
// ========================================

const MEDICAL_SPECIALTIES = [
  {
    id: 'general',
    name: 'طب عام',
    icon: '🩺',
    services: [
      { name: 'كشف عام', price: 15000 },
      { name: 'متابعة', price: 10000 },
      { name: 'فحص دوري', price: 15000 },
      { name: 'استشارة طبية', price: 20000 },
      { name: 'تضميد جرح', price: 10000 },
      { name: 'حقنة', price: 5000 },
      { name: 'قياس ضغط وسكر', price: 5000 },
    ]
  },
  {
    id: 'internal',
    name: 'باطنية',
    icon: '🫀',
    services: [
      { name: 'كشف باطنية', price: 20000 },
      { name: 'متابعة مزمن', price: 15000 },
      { name: 'استشارة', price: 25000 },
      { name: 'فحص شامل', price: 35000 },
      { name: 'تفسير تحاليل', price: 10000 },
      { name: 'تفسير أشعة', price: 10000 },
    ]
  },
  {
    id: 'pediatrics',
    name: 'طب أطفال',
    icon: '👶',
    services: [
      { name: 'كشف أطفال', price: 15000 },
      { name: 'متابعة', price: 10000 },
      { name: 'تطعيم', price: 10000 },
      { name: 'فحص نمو', price: 15000 },
      { name: 'استشارة', price: 20000 },
      { name: 'فحص حديث ولادة', price: 20000 },
    ]
  },
  {
    id: 'gynecology',
    name: 'نساء وتوليد',
    icon: '🤰',
    services: [
      { name: 'كشف نساء', price: 20000 },
      { name: 'متابعة حمل', price: 20000 },
      { name: 'سونار', price: 25000 },
      { name: 'سونار ثلاثي الأبعاد', price: 40000 },
      { name: 'تركيب لولب', price: 35000 },
      { name: 'فحص دوري', price: 20000 },
      { name: 'استشارة', price: 25000 },
      { name: 'مسحة عنق الرحم', price: 25000 },
    ]
  },
  {
    id: 'orthopedics',
    name: 'عظام ومفاصل',
    icon: '🦴',
    services: [
      { name: 'كشف عظام', price: 20000 },
      { name: 'متابعة', price: 15000 },
      { name: 'جبس', price: 30000 },
      { name: 'خلع جبس', price: 15000 },
      { name: 'حقنة مفصل', price: 35000 },
      { name: 'تضميد', price: 10000 },
      { name: 'استشارة جراحية', price: 35000 },
      { name: 'تفسير أشعة', price: 10000 },
    ]
  },
  {
    id: 'cardiology',
    name: 'قلبية وأوعية دموية',
    icon: '❤️',
    services: [
      { name: 'كشف قلب', price: 25000 },
      { name: 'تخطيط قلب ECG', price: 15000 },
      { name: 'إيكو قلب', price: 50000 },
      { name: 'متابعة', price: 20000 },
      { name: 'استشارة', price: 30000 },
      { name: 'هولتر 24 ساعة', price: 60000 },
      { name: 'تفسير تخطيط', price: 10000 },
    ]
  },
  {
    id: 'neurology',
    name: 'أعصاب',
    icon: '🧠',
    services: [
      { name: 'كشف أعصاب', price: 25000 },
      { name: 'متابعة', price: 20000 },
      { name: 'استشارة', price: 30000 },
      { name: 'تفسير MRI', price: 15000 },
      { name: 'تخطيط دماغ EEG', price: 40000 },
      { name: 'حقنة علاجية', price: 20000 },
    ]
  },
  {
    id: 'neurosurgery',
    name: 'جراحة أعصاب',
    icon: '🧬',
    services: [
      { name: 'كشف', price: 35000 },
      { name: 'استشارة جراحية', price: 50000 },
      { name: 'متابعة ما بعد عملية', price: 25000 },
      { name: 'تفسير MRI', price: 20000 },
    ]
  },
  {
    id: 'ophthalmology',
    name: 'عيون',
    icon: '👁️',
    services: [
      { name: 'كشف عيون', price: 20000 },
      { name: 'قياس نظر', price: 15000 },
      { name: 'قياس ضغط عين', price: 10000 },
      { name: 'فحص قاع العين', price: 20000 },
      { name: 'متابعة', price: 15000 },
      { name: 'حقنة عين', price: 50000 },
      { name: 'ليزر علاجي', price: 100000 },
      { name: 'استشارة', price: 25000 },
    ]
  },
  {
    id: 'ent',
    name: 'أنف وأذن وحنجرة',
    icon: '👂',
    services: [
      { name: 'كشف أنف وأذن', price: 20000 },
      { name: 'تنظيف أذن', price: 15000 },
      { name: 'فحص سمع', price: 20000 },
      { name: 'منظار أنف', price: 25000 },
      { name: 'كي أنف', price: 35000 },
      { name: 'متابعة', price: 15000 },
      { name: 'استشارة جراحية', price: 30000 },
    ]
  },
  {
    id: 'dermatology',
    name: 'جلدية وتناسلية',
    icon: '🧴',
    services: [
      { name: 'كشف جلدية', price: 20000 },
      { name: 'متابعة', price: 15000 },
      { name: 'علاج ليزر', price: 75000 },
      { name: 'حقن فيلر', price: 150000 },
      { name: 'بوتوكس', price: 150000 },
      { name: 'تقشير كيميائي', price: 75000 },
      { name: 'إزالة زوائد', price: 35000 },
      { name: 'استشارة', price: 25000 },
    ]
  },
  {
    id: 'dentistry',
    name: 'أسنان',
    icon: '🦷',
    services: [
      { name: 'كشف أسنان', price: 15000 },
      { name: 'حشو عادي', price: 25000 },
      { name: 'حشو ضوئي', price: 35000 },
      { name: 'خلع سن', price: 20000 },
      { name: 'خلع ضرس', price: 35000 },
      { name: 'تقويم أسنان (جلسة)', price: 25000 },
      { name: 'تركيب تقويم', price: 300000 },
      { name: 'تبييض أسنان', price: 100000 },
      { name: 'تنظيف جير', price: 35000 },
      { name: 'علاج عصب', price: 75000 },
      { name: 'تركيبة ثابتة (للسن)', price: 75000 },
      { name: 'زراعة سن', price: 500000 },
      { name: 'طقم أسنان كامل', price: 300000 },
    ]
  },
  {
    id: 'urology',
    name: 'مسالك بولية',
    icon: '🫘',
    services: [
      { name: 'كشف مسالك', price: 25000 },
      { name: 'سونار كلى ومثانة', price: 25000 },
      { name: 'منظار مثانة', price: 50000 },
      { name: 'متابعة', price: 20000 },
      { name: 'استشارة جراحية', price: 35000 },
      { name: 'تحطيم حصى', price: 150000 },
    ]
  },
  {
    id: 'endocrinology',
    name: 'غدد صماء وسكري',
    icon: '🔬',
    services: [
      { name: 'كشف غدد', price: 25000 },
      { name: 'متابعة سكري', price: 20000 },
      { name: 'متابعة درقية', price: 20000 },
      { name: 'استشارة', price: 30000 },
      { name: 'تفسير تحاليل هرمونية', price: 15000 },
    ]
  },
  {
    id: 'pulmonology',
    name: 'صدرية وتنفسية',
    icon: '🫁',
    services: [
      { name: 'كشف صدرية', price: 20000 },
      { name: 'تنفسية (سبيرومتري)', price: 25000 },
      { name: 'متابعة ربو', price: 15000 },
      { name: 'استشارة', price: 25000 },
      { name: 'تفسير أشعة صدر', price: 10000 },
      { name: 'بخاخ علاجي (جلسة)', price: 15000 },
    ]
  },
  {
    id: 'psychiatry',
    name: 'طب نفسي',
    icon: '🧘',
    services: [
      { name: 'جلسة نفسية', price: 30000 },
      { name: 'متابعة', price: 25000 },
      { name: 'تقييم نفسي', price: 40000 },
      { name: 'استشارة', price: 35000 },
      { name: 'جلسة علاج سلوكي', price: 35000 },
    ]
  },
  {
    id: 'general_surgery',
    name: 'جراحة عامة',
    icon: '🔪',
    services: [
      { name: 'كشف جراحي', price: 25000 },
      { name: 'استشارة جراحية', price: 35000 },
      { name: 'تضميد جرح', price: 15000 },
      { name: 'خياطة جرح', price: 35000 },
      { name: 'إزالة خيوط', price: 10000 },
      { name: 'متابعة ما بعد عملية', price: 20000 },
      { name: 'شفط خراج', price: 35000 },
    ]
  },
  {
    id: 'plastic_surgery',
    name: 'جراحة تجميل',
    icon: '✨',
    services: [
      { name: 'استشارة تجميل', price: 50000 },
      { name: 'حقن فيلر', price: 200000 },
      { name: 'بوتوكس', price: 150000 },
      { name: 'متابعة', price: 35000 },
      { name: 'إزالة وشم', price: 100000 },
    ]
  },
  {
    id: 'vascular_surgery',
    name: 'جراحة أوعية دموية',
    icon: '🩸',
    services: [
      { name: 'كشف أوعية', price: 30000 },
      { name: 'دوبلر أوعية', price: 40000 },
      { name: 'استشارة جراحية', price: 40000 },
      { name: 'متابعة', price: 25000 },
      { name: 'علاج دوالي (جلسة)', price: 75000 },
    ]
  },
  {
    id: 'rheumatology',
    name: 'روماتيزم ومفاصل',
    icon: '🦵',
    services: [
      { name: 'كشف روماتيزم', price: 25000 },
      { name: 'متابعة', price: 20000 },
      { name: 'حقنة مفصل', price: 40000 },
      { name: 'استشارة', price: 30000 },
      { name: 'تفسير تحاليل', price: 10000 },
    ]
  },
  {
    id: 'gastroenterology',
    name: 'جهاز هضمي وكبد',
    icon: '🫃',
    services: [
      { name: 'كشف هضمي', price: 25000 },
      { name: 'منظار معدة', price: 75000 },
      { name: 'منظار قولون', price: 100000 },
      { name: 'سونار بطن', price: 25000 },
      { name: 'متابعة كبد', price: 20000 },
      { name: 'استشارة', price: 30000 },
    ]
  },
  {
    id: 'nephrology',
    name: 'كلى وجهاز بولي',
    icon: '🫘',
    services: [
      { name: 'كشف كلى', price: 25000 },
      { name: 'متابعة غسيل كلى', price: 20000 },
      { name: 'استشارة', price: 30000 },
      { name: 'سونار كلى', price: 25000 },
      { name: 'تفسير تحاليل', price: 10000 },
    ]
  },
  {
    id: 'hematology',
    name: 'دم وأورام دموية',
    icon: '🩸',
    services: [
      { name: 'كشف دم', price: 25000 },
      { name: 'متابعة', price: 20000 },
      { name: 'استشارة', price: 35000 },
      { name: 'تفسير تحاليل دم', price: 15000 },
      { name: 'نقل دم (إشراف)', price: 25000 },
    ]
  },
  {
    id: 'oncology',
    name: 'أورام وسرطان',
    icon: '🎗️',
    services: [
      { name: 'كشف أورام', price: 35000 },
      { name: 'متابعة علاج كيماوي', price: 30000 },
      { name: 'استشارة', price: 50000 },
      { name: 'تفسير نتائج', price: 20000 },
    ]
  },
  {
    id: 'anesthesia',
    name: 'تخدير وعناية مركزة',
    icon: '💉',
    services: [
      { name: 'استشارة تخدير', price: 35000 },
      { name: 'متابعة ما بعد عملية', price: 25000 },
      { name: 'علاج ألم مزمن', price: 40000 },
      { name: 'حقنة فقرية', price: 75000 },
    ]
  },
  {
    id: 'radiology',
    name: 'أشعة وتصوير',
    icon: '🩻',
    services: [
      { name: 'أشعة سينية', price: 15000 },
      { name: 'سونار عام', price: 20000 },
      { name: 'سونار دوبلر', price: 35000 },
      { name: 'CT scan', price: 75000 },
      { name: 'MRI', price: 100000 },
      { name: 'تفسير أشعة', price: 15000 },
    ]
  },

  {
    id: 'physiotherapy',
    name: 'علاج طبيعي وتأهيل',
    icon: '🏃',
    services: [
      { name: 'جلسة علاج طبيعي', price: 20000 },
      { name: 'جلسة كهربائي', price: 15000 },
      { name: 'جلسة موجات صوتية', price: 20000 },
      { name: 'جلسة مغناطيس', price: 20000 },
      { name: 'جلسة شمع', price: 15000 },
      { name: 'تقييم وخطة علاجية', price: 25000 },
      { name: 'تمارين تأهيل (جلسة)', price: 20000 },
    ]
  },
  {
    id: 'nutrition',
    name: 'تغذية وسمنة',
    icon: '🥗',
    services: [
      { name: 'استشارة تغذية', price: 25000 },
      { name: 'متابعة رجيم', price: 20000 },
      { name: 'تحليل جسم (Body Composition)', price: 15000 },
      { name: 'خطة غذائية', price: 30000 },
    ]
  },
  {
    id: 'fertility',
    name: 'علاج عقم وخصوبة',
    icon: '👨‍👩‍👧',
    services: [
      { name: 'استشارة عقم', price: 35000 },
      { name: 'متابعة تحريض بويضات', price: 30000 },
      { name: 'سونار متابعة', price: 25000 },
      { name: 'تحليل سائل منوي', price: 25000 },
      { name: 'تلقيح داخل رحمي', price: 150000 },
    ]
  },
  {
    id: 'allergy',
    name: 'حساسية ومناعة',
    icon: '🌿',
    services: [
      { name: 'كشف حساسية', price: 25000 },
      { name: 'اختبار حساسية جلدي', price: 35000 },
      { name: 'متابعة', price: 20000 },
      { name: 'حقنة تحصين', price: 15000 },
      { name: 'استشارة', price: 30000 },
    ]
  },
  {
    id: 'sports_medicine',
    name: 'طب رياضي',
    icon: '⚽',
    services: [
      { name: 'كشف رياضي', price: 25000 },
      { name: 'علاج إصابة رياضية', price: 30000 },
      { name: 'متابعة تأهيل', price: 20000 },
      { name: 'استشارة', price: 30000 },
    ]
  },
  {
    id: 'geriatrics',
    name: 'طب شيخوخة',
    icon: '👴',
    services: [
      { name: 'كشف شيخوخة', price: 20000 },
      { name: 'فحص شامل', price: 35000 },
      { name: 'متابعة أمراض مزمنة', price: 15000 },
      { name: 'استشارة', price: 25000 },
    ]
  },
  {
    id: 'emergency',
    name: 'طوارئ وحوادث',
    icon: '🚨',
    services: [
      { name: 'كشف طوارئ', price: 25000 },
      { name: 'إسعاف أولي', price: 20000 },
      { name: 'خياطة جرح', price: 35000 },
      { name: 'جبس طارئ', price: 35000 },
      { name: 'حقنة طارئة', price: 10000 },
    ]
  },
  {
    id: 'family_medicine',
    name: 'طب عائلي',
    icon: '👨‍👩‍👦',
    services: [
      { name: 'كشف عائلي', price: 15000 },
      { name: 'متابعة مزمن', price: 12000 },
      { name: 'فحص دوري', price: 20000 },
      { name: 'تطعيم', price: 10000 },
      { name: 'استشارة', price: 20000 },
    ]
  },
  {
    id: 'maxillofacial',
    name: 'جراحة فم وفكين',
    icon: '🦷',
    services: [
      { name: 'كشف فم وفكين', price: 30000 },
      { name: 'خلع ضرس عقل', price: 50000 },
      { name: 'استشارة جراحية', price: 40000 },
      { name: 'متابعة', price: 25000 },
    ]
  },
  {
    id: 'audiology',
    name: 'سمعيات وتخاطب',
    icon: '🦻',
    services: [
      { name: 'فحص سمع شامل', price: 25000 },
      { name: 'جلسة تخاطب', price: 25000 },
      { name: 'برمجة سماعة', price: 35000 },
      { name: 'تقييم نطق', price: 30000 },
    ]
  },
  {
    id: 'occupational',
    name: 'علاج وظيفي',
    icon: '🤲',
    services: [
      { name: 'جلسة علاج وظيفي', price: 25000 },
      { name: 'تقييم وظيفي', price: 30000 },
      { name: 'جلسة تأهيل يد', price: 25000 },
    ]
  },

  {
    id: 'alternative',
    name: 'طب بديل وتكميلي',
    icon: '🌱',
    services: [
      { name: 'جلسة إبر صينية', price: 35000 },
      { name: 'جلسة حجامة', price: 25000 },
      { name: 'جلسة مساج علاجي', price: 30000 },
      { name: 'استشارة', price: 25000 },
    ]
  },
];



// ========================================
// تحسينات الأداء — Map للبحث السريع
// ========================================
const specialtyMap = new Map(MEDICAL_SPECIALTIES.map(s => [s.id, s]));

// جلب تخصص بالـ ID
function getSpecialtyById(id) {
  return specialtyMap.get(id) || null;
}

// جلب خدمات تخصص معين
function getServicesBySpecialty(id) {
  const specialty = getSpecialtyById(id);
  return specialty ? specialty.services : [];
}

// تنسيق السعر بالدينار العراقي
function formatPrice(price) {
  return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') + ' د.ع';
}

// حماية buildSpecialtySelect من بيئة غير متصفحية
function buildSpecialtySelect(selectId, selectedValue = '', onChangeCallback = null) {
  if (typeof document === 'undefined') return;
  const select = document.getElementById(selectId);
  if (!select) return;
  select.innerHTML = '<option value="">-- اختر التخصص --</option>';
  MEDICAL_SPECIALTIES.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.icon} ${s.name}`;
    if (s.id === selectedValue) opt.selected = true;
    select.appendChild(opt);
  });
  // تحديث قائمة الخدمات تلقائياً عند تغيير التخصص
  if (onChangeCallback) {
    select.onchange = () => onChangeCallback(select.value);
  }
}

// تصدير للبيئات المختلفة (Node.js / ES6)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MEDICAL_SPECIALTIES, specialtyMap, getSpecialtyById, getServicesBySpecialty, buildSpecialtySelect, formatPrice };
}
// دعم ES6 Modules
// export { MEDICAL_SPECIALTIES, specialtyMap, getSpecialtyById, getServicesBySpecialty, buildSpecialtySelect, formatPrice };
