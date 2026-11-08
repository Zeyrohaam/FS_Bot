const tg = window.Telegram?.WebApp;
const rawInitData = (tg?.initData || '').trim();
// The MiniApp is ONLY operational if launched inside Telegram with genuine initData
const isTelegramApp = Boolean(rawInitData && rawInitData.length > 5);

if (tg && isTelegramApp) {
  try {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor('secondary_bg_color');
    if (tg.setBottomBarColor) tg.setBottomBarColor('secondary_bg_color');
  } catch (_) {}
}

function enforceTelegramClient() {
  if (!isTelegramApp) {
    const screen = document.getElementById('telegramRequiredScreen');
    if (screen) screen.classList.remove('hidden');
    const appShell = document.getElementById('app') || document.querySelector('.app');
    if (appShell) appShell.style.display = 'none';
    const mainNav = document.querySelector('.bottom-nav, .nav');
    if (mainNav) mainNav.style.display = 'none';
    return false;
  }
  return true;
}

const state = {
  initData: isTelegramApp ? rawInitData : '',
  bootstrap: null,
  pendingProof: null,
  isUploadingProof: false,
  minesSession: null,
  activeGame: null,
  rouletteRotation: 0,
  crashAnimating: false,
  crashSession: null,
  crashActive: false,
  crashCurrentX: 1.0,
  caseOpening: false,
  bootstrapLoading: false,
  casino: null,
  nftQuotes: {},
  adminDashboard: null,
  adminTrackedUserId: null,
};

enforceTelegramClient();

function initSpaceBackdrop() {
  const field = document.getElementById('spaceField');
  if (!field) return;

  const existing = field.querySelectorAll('.space-star, .space-shooting-star, .space-rocket');
  existing.forEach((node) => node.remove());

  const starCount = 26;
  for (let i = 0; i < starCount; i += 1) {
    const star = document.createElement('span');
    star.className = 'space-star';
    const size = 2 + Math.random() * 4;
    star.style.setProperty('--size', `${size}px`);
    star.style.left = `${Math.random() * 100}%`;
    star.style.top = `${Math.random() * 100}%`;
    star.style.setProperty('--dur', `${3 + Math.random() * 5}s`);
    star.style.animationDelay = `${Math.random() * 4}s`;
    star.style.opacity = String(0.35 + Math.random() * 0.65);
    field.appendChild(star);
  }

  const rocket = document.createElement('span');
  rocket.className = 'space-rocket';
  rocket.style.left = '110%';
  rocket.style.top = `${18 + Math.random() * 26}%`;
  rocket.style.animationDelay = `${2 + Math.random() * 7}s`;
  field.appendChild(rocket);

  const launchTrail = () => {
    const trail = document.createElement('span');
    trail.className = 'space-shooting-star';
    trail.style.left = `${Math.random() * 42}%`;
    trail.style.top = `${Math.random() * 44}%`;
    trail.style.setProperty('--rot', `${-18 - Math.random() * 20}deg`);
    trail.style.setProperty('--speed', `${2.2 + Math.random() * 2.1}s`);
    trail.style.animationDelay = '0s';
    field.appendChild(trail);
    setTimeout(() => trail.remove(), 2600);
  };

  const loopShots = () => {
    if (Math.random() < 0.8) {
      launchTrail();
    }
    const nextDelay = 1800 + Math.random() * 4200;
    setTimeout(loopShots, nextDelay);
  };

  setTimeout(loopShots, 1600);

  setInterval(() => {
    const extra = document.createElement('span');
    extra.className = 'space-rocket';
    extra.style.left = '110%';
    extra.style.top = `${10 + Math.random() * 34}%`;
    extra.style.animationDuration = `${14 + Math.random() * 12}s`;
    extra.style.animationDelay = '0s';
    field.appendChild(extra);
    setTimeout(() => extra.remove(), 20000);
  }, 19000);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSpaceBackdrop, { once: true });
} else {
  initSpaceBackdrop();
}

const DEFAULT_NFT_GIFTS = [{"kind": "gift", "model": "jingle-bells", "name": "Jingle Bells", "label": "Jingle Bells", "value": 310, "unit": "⭐", "image": "https://nft.fragment.com/gift/jinglebells-17151.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "big-year", "name": "Big Year", "label": "Big Year", "value": 319, "unit": "⭐", "image": "https://nft.fragment.com/gift/BigYear-57523.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "ice-cream", "name": "Ice Cream", "label": "Ice Cream", "value": 319, "unit": "⭐", "image": "https://nft.fragment.com/gift/IceCream-44643.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "pool-float", "name": "Pool Float", "label": "Pool Float", "value": 322, "unit": "⭐", "image": "https://nft.fragment.com/gift/PoolFloat-48197.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "candy-cane", "name": "Candy Cane", "label": "Candy Cane", "value": 327, "unit": "⭐", "image": "https://nft.fragment.com/gift/CandyCane-67654.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "instant-ramen", "name": "Instant Ramen", "label": "Instant Ramen", "value": 331, "unit": "⭐", "image": "https://nft.fragment.com/gift/InstantRamen-10211.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "ginger-cookie", "name": "Ginger Cookie", "label": "Ginger Cookie", "value": 355, "unit": "⭐", "image": "https://nft.fragment.com/gift/GingerCookie-55077.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "santa-hat", "name": "Santa Hat", "label": "Santa Hat", "value": 390, "unit": "⭐", "image": "https://nft.fragment.com/gift/santahat-16799.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "liberty-figure", "name": "Statue of Liberty", "label": "Statue of Liberty", "value": 394, "unit": "⭐", "image": "https://nft.fragment.com/gift/libertyfigure-115871.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "homemade-cake", "name": "Homemade Cake", "label": "Homemade Cake", "value": 420, "unit": "⭐", "image": "https://nft.fragment.com/gift/homemadecake-35678.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "chester-hat", "name": "Jester Hat", "label": "Jester Hat", "value": 436, "unit": "⭐", "image": "https://nft.fragment.com/gift/JesterHat-101105.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "desk-calendar", "name": "Desk Calendar", "label": "Desk Calendar", "value": 449, "unit": "⭐", "image": "https://nft.fragment.com/gift/DeskCalendar-86441.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "spiced-wine", "name": "Spiced Wine", "label": "Spiced Wine", "value": 450, "unit": "⭐", "image": "https://nft.fragment.com/gift/spicedwine-30494.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "toy-bear", "name": "Toy Bear", "label": "Toy Bear", "value": 480, "unit": "⭐", "image": "https://nft.fragment.com/gift/toybear-5257.medium.jpg", "icon": "🎁", "rarity": "common"}, {"kind": "gift", "model": "jelly-bunny", "name": "Jelly Bunny", "label": "Jelly Bunny", "value": 520, "unit": "⭐", "image": "https://nft.fragment.com/gift/jellybunny-66085.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "lush-bouquet", "name": "Lush Bouquet", "label": "Lush Bouquet", "value": 535, "unit": "⭐", "image": "https://nft.fragment.com/gift/LushBouquet-30203.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "stellar-rocket", "name": "Stellar Rocket", "label": "Stellar Rocket", "value": 543, "unit": "⭐", "image": "https://nft.fragment.com/gift/StellarRocket-96957.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "snow-globe", "name": "Snow Globe", "label": "Snow Globe", "value": 550, "unit": "⭐", "image": "https://nft.fragment.com/gift/snowglobe-17571.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "sharp-tongue", "name": "Sharp Tongue", "label": "Sharp Tongue", "value": 600, "unit": "⭐", "image": "https://nft.fragment.com/gift/sharptongue-1511.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "bunny-mafin", "name": "Bunny Muffin", "label": "Bunny Muffin", "value": 682, "unit": "⭐", "image": "https://nft.fragment.com/gift/BunnyMuffin-42417.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "berry-box", "name": "Berry Box", "label": "Berry Box", "value": 684, "unit": "⭐", "image": "https://nft.fragment.com/gift/BerryBox-36312.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "love-candle", "name": "Love Candle", "label": "Love Candle", "value": 716, "unit": "⭐", "image": "https://nft.fragment.com/gift/LoveCandle-6779.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "perfume-bottle", "name": "Perfume Bottle", "label": "Perfume Bottle", "value": 850, "unit": "⭐", "image": "https://nft.fragment.com/gift/perfumebottle-2822.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "flying-broom", "name": "Flying Broom", "label": "Flying Broom", "value": 889, "unit": "⭐", "image": "https://nft.fragment.com/gift/FlyingBroom-14892.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "heart-box", "name": "Heart Box", "label": "Heart Box", "value": 890, "unit": "⭐", "image": "https://nft.fragment.com/gift/valentinebox-999.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "vintage-cigar", "name": "Vintage Cigar", "label": "Vintage Cigar", "value": 920, "unit": "⭐", "image": "https://nft.fragment.com/gift/vintagecigar-5974.medium.jpg", "icon": "🎁", "rarity": "rare"}, {"kind": "gift", "model": "crystal-ball", "name": "Crystal Ball", "label": "Crystal Ball", "value": 1053, "unit": "⭐", "image": "https://nft.fragment.com/gift/CrystalBall-22131.medium.jpg", "icon": "🎁", "rarity": "epic"}, {"kind": "gift", "model": "ufc-box", "name": "UFC Strike", "label": "UFC Strike", "value": 1221, "unit": "⭐", "image": "https://nft.fragment.com/gift/UFCStrike-1718.medium.jpg", "icon": "🎁", "rarity": "epic"}, {"kind": "gift", "model": "swiss-watch", "name": "Swiss Watch", "label": "Swiss Watch", "value": 1500, "unit": "⭐", "image": "https://nft.fragment.com/gift/swisswatch-18663.medium.jpg", "icon": "🎁", "rarity": "epic"}, {"kind": "gift", "model": "mini-oscar", "name": "Mini Oscar", "label": "Mini Oscar", "value": 1750, "unit": "⭐", "image": "https://nft.fragment.com/gift/minioscar-2207.medium.jpg", "icon": "🎁", "rarity": "epic"}, {"kind": "gift", "model": "ion-gem", "name": "Ion Gem", "label": "Ion Gem", "value": 2100, "unit": "⭐", "image": "https://nft.fragment.com/gift/iongem-3514.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "eternal-rose", "name": "Eternal Rose", "label": "Eternal Rose", "value": 2231, "unit": "⭐", "image": "https://nft.fragment.com/gift/EternalRose-2743.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "diamond-ring", "name": "Diamond Ring", "label": "Diamond Ring", "value": 2800, "unit": "⭐", "image": "https://nft.fragment.com/gift/diamondring-9059.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "genie-lamp", "name": "Genie Lamp", "label": "Genie Lamp", "value": 3124, "unit": "⭐", "image": "https://nft.fragment.com/gift/GenieLamp-4819.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "precious-peach", "name": "Precious Peach", "label": "Precious Peach", "value": 3400, "unit": "⭐", "image": "https://nft.fragment.com/gift/preciouspeach-246.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "bonded-rind", "name": "Bonded Ring", "label": "Bonded Ring", "value": 3696, "unit": "⭐", "image": "https://nft.fragment.com/gift/BondedRing-3010.medium.jpg", "icon": "🎁", "rarity": "legendary"}, {"kind": "gift", "model": "durov-cap", "name": "Durov's Cap", "label": "Durov's Cap", "value": 4500, "unit": "⭐", "image": "https://nft.fragment.com/gift/durovscap-501.medium.jpg", "icon": "🎁", "rarity": "mythic"}, {"kind": "gift", "model": "magic-potion", "name": "Magic Potion", "label": "Magic Potion", "value": 4926, "unit": "⭐", "image": "https://nft.fragment.com/gift/MagicPotion-3919.medium.jpg", "icon": "🎁", "rarity": "mythic"}, {"kind": "gift", "model": "plush-pepe", "name": "Plush Pepe", "label": "Plush Pepe", "value": 8000, "unit": "⭐", "image": "https://nft.fragment.com/gift/plushpepe-1056.medium.jpg", "icon": "🎁", "rarity": "mythic"}, {"kind": "gift", "model": "loot-bag", "name": "Loot Bag", "label": "Loot Bag", "value": 11563, "unit": "⭐", "image": "https://nft.fragment.com/gift/LootBag-1779.medium.jpg", "icon": "🎁", "rarity": "mythic"}, {"kind": "gift", "model": "astral-shard", "name": "Astral Shard", "label": "Astral Shard", "value": 11953, "unit": "⭐", "image": "https://nft.fragment.com/gift/AstralShard-3750.medium.jpg", "icon": "🎁", "rarity": "mythic"}];

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const STARS_PER_USDT = 75;

const COMMON_CASE_GIFT_CHANCE_PERCENT = {
  'lush-bouquet': 4.0,
  'pool-float': 4.0,
  'instant-ramen': 5.0,
  'ice-cream': 5.64,
  'ufc-box': 3.0,
  'ginger-cookie': 18.0,
  'liberty-figure': 15.0,
  'bunny-mafin': 16.0,
  'crystal-ball': 11.0,
  'eternal-rose': 6.1,
  'magic-potion': 0.05,
  'astral-shard': 0.0,
  'candy-cane': 14.9,
  'love-candle': 8.2,
  'flying-broom': 4.9,
  'genie-lamp': 0.2,
  'loot-bag': 0.0,
  'desk-calendar': 2.1,
  'big-year': 3.2,
  'berry-box': 1.5,
  'bonded-rind': 0.01,
  'stellar-rocket': 2.0,
  'chester-hat': 2.5,
};

function getAdminCaseChancePercent(item) {
  const model = String(item?.model || '').trim().toLowerCase();
  const configured = state.bootstrap?.pricing?.nft_case_chances || {};
  if (model && Object.prototype.hasOwnProperty.call(configured, model)) {
    const parsed = Number(configured[model]);
    if (Number.isFinite(parsed) && parsed >= 0) return parsed;
  }
  return 0;
}

function getItemChancePercent(item) {
  const adminChance = getAdminCaseChancePercent(item);
  if (adminChance > 0) {
    return adminChance;
  }
  const model = String(item?.model || '').trim().toLowerCase();
  if (model && Object.prototype.hasOwnProperty.call(COMMON_CASE_GIFT_CHANCE_PERCENT, model)) {
    return Number(COMMON_CASE_GIFT_CHANCE_PERCENT[model]);
  }
  const explicit = Number(item?.chancePercent ?? item?.chance_percent ?? item?.weight ?? 0);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  return 0;
}

function formatRewardValueLine(item) {
  const base = `${fmt(item.value, 0)} ${item.unit}`;
  return base;
}

let _cachedStarDropArtwork = null;
let _cachedGiftPlaceholderArtwork = null;

function makeStarDropArtwork() {
  if (_cachedStarDropArtwork) return _cachedStarDropArtwork;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">
  <defs>
    <radialGradient id="starBg" cx="50%" cy="45%" r="65%">
      <stop offset="0%" stop-color="#2a1b54"/>
      <stop offset="55%" stop-color="#130e2e"/>
      <stop offset="100%" stop-color="#080a16"/>
    </radialGradient>
    <linearGradient id="starBrd" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffd54f" stop-opacity="0.6"/>
      <stop offset="50%" stop-color="#8b5cf6" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#ff9100" stop-opacity="0.5"/>
    </linearGradient>
    <radialGradient id="starBloom" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffb300" stop-opacity="0.65"/>
      <stop offset="50%" stop-color="#ff8f00" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#ff6f00" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="starCore" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9"/>
      <stop offset="40%" stop-color="#ffe082" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#ffb300" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="starHalo" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffe082" stop-opacity="0.6"/>
      <stop offset="50%" stop-color="#ff9800" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#ffd54f" stop-opacity="0.5"/>
    </linearGradient>
    <linearGradient id="fTL" x1="20%" y1="0%" x2="80%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="40%" stop-color="#fff59d"/>
      <stop offset="100%" stop-color="#fbc02d"/>
    </linearGradient>
    <linearGradient id="fTR" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffe082"/>
      <stop offset="100%" stop-color="#f57f17"/>
    </linearGradient>
    <linearGradient id="fRT" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fff176"/>
      <stop offset="100%" stop-color="#fbc02d"/>
    </linearGradient>
    <linearGradient id="fRB" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f57f17"/>
      <stop offset="100%" stop-color="#e65100"/>
    </linearGradient>
    <linearGradient id="fBRT" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffa726"/>
      <stop offset="100%" stop-color="#f57c00"/>
    </linearGradient>
    <linearGradient id="fBRB" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f57c00"/>
      <stop offset="100%" stop-color="#bf360c"/>
    </linearGradient>
    <linearGradient id="fBLR" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fb8c00"/>
      <stop offset="100%" stop-color="#d84315"/>
    </linearGradient>
    <linearGradient id="fBLL" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffb74d"/>
      <stop offset="100%" stop-color="#f57c00"/>
    </linearGradient>
    <linearGradient id="fLB" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffe082"/>
      <stop offset="100%" stop-color="#f57f17"/>
    </linearGradient>
    <linearGradient id="fLT" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fff9c4"/>
      <stop offset="60%" stop-color="#ffd54f"/>
      <stop offset="100%" stop-color="#fbc02d"/>
    </linearGradient>
    <filter id="starShadow" x="-20%" y="-20%" width="150%" height="150%">
      <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#e65100" flood-opacity="0.55"/>
    </filter>
  </defs>
  <rect x="3" y="3" width="234" height="234" rx="36" fill="url(#starBg)" stroke="url(#starBrd)" stroke-width="1.8"/>
  <circle cx="120" cy="118" r="96" fill="url(#starBloom)"/>
  <circle cx="120" cy="118" r="86" fill="none" stroke="url(#starHalo)" stroke-width="1.5" stroke-dasharray="6 8" opacity="0.6"/>
  <g fill="#ffd54f" opacity="0.9">
    <path d="M204 36 Q204 46 214 46 Q204 46 204 56 Q204 46 194 46 Q204 46 204 36 Z" fill="#ffffff"/>
    <circle cx="204" cy="46" r="2" fill="#ffd54f"/>
    <path d="M38 42 Q38 49 45 49 Q38 49 38 56 Q38 49 31 49 Q38 49 38 42 Z" fill="#ffe082" opacity="0.8"/>
    <path d="M32 186 Q32 192 38 192 Q32 192 32 198 Q32 192 26 192 Q32 192 32 186 Z" fill="#ffe082" opacity="0.75"/>
    <path d="M208 184 Q208 191 215 191 Q208 191 208 198 Q208 191 201 191 Q208 191 208 184 Z" fill="#ffd54f" opacity="0.8"/>
    <circle cx="48" cy="116" r="1.8" fill="#ffffff" opacity="0.6"/>
    <circle cx="194" cy="118" r="1.8" fill="#ffffff" opacity="0.6"/>
  </g>
  <g filter="url(#starShadow)">
    <polygon points="120,28 142,89.9 205.6,90.2 155.6,131.6 172.9,190.8 120,155.5 67.1,190.8 84.4,131.6 34.4,90.2 98,89.9" fill="#ff8f00" opacity="0.25" transform="translate(0, 4)"/>
    <polygon points="120,118 98,89.9 120,28" fill="url(#fTL)"/>
    <polygon points="120,118 120,28 142,89.9" fill="url(#fTR)"/>
    <polygon points="120,118 142,89.9 205.6,90.2" fill="url(#fRT)"/>
    <polygon points="120,118 205.6,90.2 155.6,131.6" fill="url(#fRB)"/>
    <polygon points="120,118 155.6,131.6 172.9,190.8" fill="url(#fBRT)"/>
    <polygon points="120,118 172.9,190.8 120,155.5" fill="url(#fBRB)"/>
    <polygon points="120,118 120,155.5 67.1,190.8" fill="url(#fBLR)"/>
    <polygon points="120,118 67.1,190.8 84.4,131.6" fill="url(#fBLL)"/>
    <polygon points="120,118 84.4,131.6 34.4,90.2" fill="url(#fLB)"/>
    <polygon points="120,118 34.4,90.2 98,89.9" fill="url(#fLT)"/>
  </g>
  <circle cx="120" cy="32" r="3.5" fill="#ffffff"/>
  <ellipse cx="120" cy="32" rx="14" ry="4" fill="#ffffff" opacity="0.8" transform="rotate(-15 120 32)"/>
  <circle cx="36" cy="90" r="2.5" fill="#ffffff"/>
  <ellipse cx="36" cy="90" rx="8" ry="2.5" fill="#ffffff" opacity="0.7" transform="rotate(35 36 90)"/>
  <circle cx="120" cy="118" r="24" fill="url(#starCore)" opacity="0.7"/>
</svg>`;
  _cachedStarDropArtwork = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  return _cachedStarDropArtwork;
}

function makeGiftPlaceholderArtwork() {
  if (_cachedGiftPlaceholderArtwork) return _cachedGiftPlaceholderArtwork;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="240" height="240">
  <defs>
    <radialGradient id="gBg" cx="50%" cy="45%" r="65%">
      <stop offset="0%" stop-color="#271247"/>
      <stop offset="55%" stop-color="#120c2b"/>
      <stop offset="100%" stop-color="#080916"/>
    </radialGradient>
    <linearGradient id="gBrd" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#c084fc" stop-opacity="0.65"/>
      <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#f43f5e" stop-opacity="0.55"/>
    </linearGradient>
    <radialGradient id="gAura" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#9333ea" stop-opacity="0.55"/>
      <stop offset="50%" stop-color="#6366f1" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#9333ea" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="lidTop" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#6b21a8"/>
    </linearGradient>
    <linearGradient id="lidSkL" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#9333ea"/>
      <stop offset="100%" stop-color="#581c87"/>
    </linearGradient>
    <linearGradient id="lidSkR" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#4c1d95"/>
      <stop offset="100%" stop-color="#2e1065"/>
    </linearGradient>
    <linearGradient id="boxBL" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7e22ce"/>
      <stop offset="100%" stop-color="#3b0764"/>
    </linearGradient>
    <linearGradient id="boxBR" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4c1d95"/>
      <stop offset="100%" stop-color="#1e0a3d"/>
    </linearGradient>
    <linearGradient id="gRibL" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="30%" stop-color="#fff59d"/>
      <stop offset="70%" stop-color="#fbc02d"/>
      <stop offset="100%" stop-color="#f57f17"/>
    </linearGradient>
    <linearGradient id="gRibR" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbc02d"/>
      <stop offset="100%" stop-color="#d84315"/>
    </linearGradient>
    <radialGradient id="ped" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.65"/>
      <stop offset="60%" stop-color="#38bdf8" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="starEmb" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="50%" stop-color="#ffd54f"/>
      <stop offset="100%" stop-color="#f57f17"/>
    </linearGradient>
    <filter id="gBoxShd" x="-20%" y="-20%" width="150%" height="150%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#000000" flood-opacity="0.65"/>
    </filter>
  </defs>
  <rect x="3" y="3" width="234" height="234" rx="36" fill="url(#gBg)" stroke="url(#gBrd)" stroke-width="1.8"/>
  <circle cx="120" cy="124" r="94" fill="url(#gAura)"/>
  <ellipse cx="120" cy="192" rx="66" ry="16" fill="url(#ped)"/>
  <ellipse cx="120" cy="192" rx="52" ry="11" fill="none" stroke="#a855f7" stroke-width="1.5" stroke-dasharray="4 6" opacity="0.7"/>
  <g fill="#ffffff" opacity="0.9">
    <path d="M204 42 Q204 51 213 51 Q204 51 204 60 Q204 51 195 51 Q204 51 204 42 Z" fill="#ffffff"/>
    <circle cx="204" cy="51" r="1.8" fill="#ffd54f"/>
    <path d="M36 46 Q36 53 43 53 Q36 53 36 60 Q36 53 29 53 Q36 53 36 46 Z" fill="#c084fc" opacity="0.85"/>
    <path d="M206 172 Q206 178 212 178 Q206 178 206 184 Q206 178 200 178 Q206 178 206 172 Z" fill="#38bdf8" opacity="0.8"/>
    <path d="M34 170 Q34 175 39 175 Q34 175 34 180 Q34 175 29 175 Q34 175 34 170 Z" fill="#f43f5e" opacity="0.75"/>
    <circle cx="42" cy="112" r="1.5" fill="#ffffff" opacity="0.6"/>
    <circle cx="198" cy="114" r="1.5" fill="#ffffff" opacity="0.6"/>
  </g>
  <g filter="url(#gBoxShd)">
    <polygon points="68,104 120,128 120,180 68,154" fill="url(#boxBL)"/>
    <polygon points="120,128 172,104 172,154 120,180" fill="url(#boxBR)"/>
    <polygon points="91,114 98,118 98,169 91,165" fill="url(#gRibL)"/>
    <polygon points="142,118 149,114 149,165 142,169" fill="url(#gRibR)"/>
    <line x1="93" y1="116" x2="93" y2="166" stroke="#ffffff" stroke-width="1.2" opacity="0.55"/>
    <g transform="translate(120, 150)">
      <circle cx="0" cy="0" r="14" fill="#1e0a3d" stroke="#ffd54f" stroke-width="1.5" opacity="0.95"/>
      <circle cx="0" cy="0" r="16" fill="none" stroke="#ffd54f" stroke-width="1" opacity="0.4" stroke-dasharray="2 4"/>
      <polygon points="0,-8 2.4,-2.5 8,-2 3.8,1.8 5.2,7.5 0,4.5 -5.2,7.5 -3.8,1.8 -8,-2 -2.4,-2.5" fill="url(#starEmb)"/>
      <circle cx="0" cy="0" r="2" fill="#ffffff"/>
    </g>
    <polygon points="64,92 120,118 120,126 64,101" fill="url(#lidSkL)"/>
    <polygon points="120,118 176,92 176,101 120,126" fill="url(#lidSkR)"/>
    <polygon points="120,68 176,92 120,118 64,92" fill="url(#lidTop)"/>
    <polygon points="89,79 96,82 151,106 144,103" fill="url(#gRibL)" opacity="0.95"/>
    <polygon points="151,79 144,82 89,106 96,103" fill="url(#gRibR)" opacity="0.9"/>
    <ellipse cx="120" cy="92" rx="11" ry="6" fill="#b45309" opacity="0.7"/>
    <path d="M120,89 C102,60 66,66 80,88 C90,100 112,94 120,90 Z" fill="url(#gRibL)"/>
    <path d="M116,87 C105,71 80,75 90,89 C97,96 112,92 116,88 Z" fill="#b45309" opacity="0.45"/>
    <path d="M118,87 C105,68 76,73 86,87" stroke="#ffffff" stroke-width="1.4" fill="none" opacity="0.75"/>
    <path d="M120,90 C128,94 150,100 160,88 C174,66 138,60 120,89 Z" fill="url(#gRibR)"/>
    <path d="M124,88 C128,92 143,96 150,89 C160,75 135,71 124,87 Z" fill="#78350f" opacity="0.45"/>
    <path d="M122,87 C135,68 164,73 154,87" stroke="#ffffff" stroke-width="1.2" fill="none" opacity="0.5"/>
    <path d="M117,92 Q103,108 97,126 Q105,122 112,110 Q117,99 119,93 Z" fill="url(#gRibL)"/>
    <path d="M123,92 Q137,108 143,126 Q135,122 128,110 Q123,99 121,93 Z" fill="url(#gRibR)"/>
    <circle cx="120" cy="90" r="6" fill="#fff59d"/>
    <circle cx="120" cy="90" r="4.5" fill="#f59e0b"/>
    <circle cx="118" cy="88" r="1.8" fill="#ffffff"/>
  </g>
  <ellipse cx="120" cy="118" rx="8" ry="2.5" fill="#ffffff" opacity="0.7"/>
</svg>`;
  _cachedGiftPlaceholderArtwork = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  return _cachedGiftPlaceholderArtwork;
}

function createArtwork(kind) {
  if (kind === 'stars') return makeStarDropArtwork();
  return makeGiftPlaceholderArtwork();
}

function getRewardImage(item) {
  if (item?.image) return item.image;
  if (item?.fallbackImage) return item.fallbackImage;
  if (item?.kind === 'stars') return makeStarDropArtwork();
  return makeGiftPlaceholderArtwork();
}

function getRewardImageErrorFallback(item) {
  if (item?.fallbackImage) return item.fallbackImage;
  if (item?.kind === 'stars') return makeStarDropArtwork();
  return makeGiftPlaceholderArtwork();
}

function getInventoryItemImage(item) {
  if (!item) return makeGiftPlaceholderArtwork();
  if (item.kind === 'gift') {
    const model = String(item.model || '').trim().toLowerCase();
    const imageMap = state.bootstrap?.pricing?.nft_gift_images || {};
    const externalImage = String(imageMap?.[model] || '').trim();
    if (/^https?:\/\//i.test(externalImage)) return externalImage;
    if (item.image && !/^https?:\/\//i.test(item.image) && item.image.startsWith('/webapp/assets/cases/')) {
      return item.image;
    }
    return item.fallbackImage || makeGiftPlaceholderArtwork();
  }
  return item.image || item.fallbackImage || makeStarDropArtwork();
}

function getInventoryItemImageErrorFallback(item) {
  if (!item) return makeGiftPlaceholderArtwork();
  if (item.kind === 'gift') {
    return item.fallbackImage || makeGiftPlaceholderArtwork();
  }
  return item.fallbackImage || makeStarDropArtwork();
}

const CASE_LIBRARY = {
  basic: { label: 'Деревянный кейс', cost: 100, minReward: 35, maxReward: 110 },
  silver: { label: 'Серебряный кейс', cost: 280, minReward: 90, maxReward: 260 },
  gold: { label: 'Алмазный кейс', cost: 720, minReward: 220, maxReward: 620 },
  case150: { label: 'Летний кейс (150⭐️)', cost: 150, minReward: 25, maxReward: 1200 },
  case250: { label: 'Завоз (250⭐️)', cost: 250, minReward: 25, maxReward: 3768 },
  case400: { label: 'Богатый (400⭐️)', cost: 400, minReward: 50, maxReward: 3768 },
  case600: { label: 'Лакшери (600⭐️)', cost: 600, minReward: 200, maxReward: 5500 },
};

function getRarityByStars(price) {
  const p = Number(price || 0);
  if (p >= 4500) return 'mythic';
  if (p >= 2000) return 'legendary';
  if (p >= 1000) return 'epic';
  if (p >= 500) return 'rare';
  return 'common';
}

const CASE150_DROP_TABLE = [
  {
    kind: 'stars',
    label: '25 звёзд',
    name: '25 звёзд',
    value: 25,
    unit: '⭐',
    icon: '⭐',
    rarity: 'common',
    chancePercent: 73.86,
    weight: 7386,
    image: createArtwork('stars', '25 звёзд', '#ffcf4d', '#ff6b35'),
  },
  {
    kind: 'gift',
    label: 'Lush Bouquet',
    name: 'Lush Bouquet',
    model: 'lush-bouquet',
    value: 517,
    unit: '⭐',
    icon: '💐',
    rarity: 'legendary',
    chancePercent: 4.0,
    weight: 400,
    image: '/webapp/assets/cases/lush-bouquet.png',
    fallbackImage: createArtwork('gift', 'Lush Bouquet', '#ec4899', '#fbcfe8'),
  },
  {
    kind: 'gift',
    label: 'Pool Float',
    name: 'Pool Float',
    model: 'pool-float',
    value: 375,
    unit: '⭐',
    icon: '🦒',
    rarity: 'epic',
    chancePercent: 4.0,
    weight: 400,
    image: '/webapp/assets/cases/pool-float.png',
    fallbackImage: createArtwork('gift', 'Pool Float', '#a16207', '#fde68a'),
  },
  {
    kind: 'gift',
    label: 'Instant Ramen',
    name: 'Instant Ramen',
    model: 'instant-ramen',
    value: 337,
    unit: '⭐',
    icon: '🍜',
    rarity: 'epic',
    chancePercent: 5.0,
    weight: 500,
    image: '/webapp/assets/cases/instant-ramen.png',
    fallbackImage: createArtwork('gift', 'Instant Ramen', '#fb923c', '#fef3c7'),
  },
  {
    kind: 'gift',
    label: 'Ice Cream',
    name: 'Ice Cream',
    model: 'ice-cream',
    value: 370,
    unit: '⭐',
    icon: '🍦',
    rarity: 'epic',
    chancePercent: 5.64,
    weight: 564,
    image: '/webapp/assets/cases/ice-cream.png',
    fallbackImage: createArtwork('gift', 'Ice Cream', '#60a5fa', '#dbeafe'),
  },
  {
    kind: 'gift',
    label: 'UFC Strike',
    name: 'UFC Strike',
    model: 'ufc-box',
    value: 1200,
    unit: '⭐',
    icon: '🥊',
    rarity: 'mythic',
    chancePercent: 3.0,
    weight: 300,
    image: '/webapp/assets/cases/ufc-box.png',
    fallbackImage: createArtwork('gift', 'UFC Strike', '#ef4444', '#fee2e2'),
  },
  {
    kind: 'gift',
    label: 'Stellar Rocket',
    name: 'Stellar Rocket',
    model: 'stellar-rocket',
    value: 1100,
    unit: '⭐',
    icon: '🚀',
    rarity: 'epic',
    chancePercent: 2.0,
    weight: 200,
    image: null,
    fallbackImage: createArtwork('gift', 'Stellar Rocket', '#0369a1', '#cffafe', '🚀'),
  },
  {
    kind: 'gift',
    label: 'Jester Hat',
    name: 'Jester Hat',
    model: 'chester-hat',
    value: 950,
    unit: '⭐',
    icon: '🎩',
    rarity: 'epic',
    chancePercent: 2.5,
    weight: 250,
    image: null,
    fallbackImage: createArtwork('gift', 'Jester Hat', '#7c3aed', '#e9d5ff', '🎩'),
  },
];

const CASE400_DROP_TABLE = [
  {
    kind: 'stars', label: '50 звёзд', name: '50 звёзд', value: 50, unit: '⭐', icon: '⭐', rarity: 'common', chancePercent: 25.1, weight: 2510,
    image: createArtwork('stars', '50 звёзд', '#f59e0b', '#fde68a'),
  },
  {
    kind: 'stars', label: '100 звёзд', name: '100 звёзд', value: 100, unit: '⭐', icon: '⭐', rarity: 'common', chancePercent: 25.1, weight: 2510,
    image: createArtwork('stars', '100 звёзд', '#22d3ee', '#2563eb'),
  },
  {
    kind: 'gift', label: 'Candy Cane', name: 'Candy Cane', model: 'candy-cane', value: 370, unit: '⭐', icon: '🍬', rarity: 'rare', chancePercent: 14.9, weight: 1490,
    fallbackImage: createArtwork('gift', 'Candy Cane', '#ef4444', '#fca5a5'),
  },
  {
    kind: 'gift', label: 'Liberty Figure', name: 'Liberty Figure', model: 'liberty-figure', value: 335, unit: '⭐', icon: '🗽', rarity: 'rare', chancePercent: 16.3, weight: 1630,
    fallbackImage: createArtwork('gift', 'Liberty', '#60a5fa', '#bfdbfe'),
  },
  {
    kind: 'gift', label: 'Love Candle', name: 'Love Candle', model: 'love-candle', value: 731, unit: '⭐', icon: '🕯️', rarity: 'epic', chancePercent: 8.2, weight: 820,
    fallbackImage: createArtwork('gift', 'Love Candle', '#fb7185', '#fbcfe8'),
  },
  {
    kind: 'gift', label: 'Crystal Ball', name: 'Crystal Ball', model: 'crystal-ball', value: 1100, unit: '⭐', icon: '🔮', rarity: 'epic', chancePercent: 5.3, weight: 530,
    fallbackImage: createArtwork('gift', 'Crystal Ball', '#a78bfa', '#ddd6fe'),
  },
  {
    kind: 'gift', label: 'Flying Broom', name: 'Flying Broom', model: 'flying-broom', value: 1057, unit: '⭐', icon: '🧹', rarity: 'epic', chancePercent: 4.9, weight: 490,
    fallbackImage: createArtwork('gift', 'Broom', '#a16207', '#fde68a'),
  },
  {
    kind: 'gift', label: 'Genie Lamp', name: 'Genie Lamp', model: 'genie-lamp', value: 2200, unit: '⭐', icon: '🪔', rarity: 'legendary', chancePercent: 0.2, weight: 20,
    fallbackImage: createArtwork('gift', 'Genie Lamp', '#f59e0b', '#fef3c7'),
  },
  {
    kind: 'gift', label: 'Loot Bag', name: 'Loot Bag', model: 'loot-bag', value: 3768, unit: '⭐', icon: '👜', rarity: 'mythic', chancePercent: 0.0, weight: 0,
    fallbackImage: createArtwork('gift', 'Loot Bag', '#475569', '#e2e8f0'),
  },
];

const CASE250_DROP_TABLE = [
  {
    kind: 'stars', label: '25 звёзд', name: '25 звёзд', value: 25, unit: '⭐', icon: '⭐', rarity: 'common', chancePercent: 43.79, weight: 4379,
    image: createArtwork('stars', '25 звёзд', '#f59e0b', '#fde68a'),
  },
  {
    kind: 'stars', label: '75 звёзд', name: '75 звёзд', value: 75, unit: '⭐', icon: '⭐', rarity: 'common', chancePercent: 43.79, weight: 4379,
    image: createArtwork('stars', '75 звёзд', '#22d3ee', '#2563eb'),
  },
  {
    kind: 'gift', label: 'Ice Cream', name: 'Ice Cream', model: 'ice-cream', value: 370, unit: '⭐', icon: '🍦', rarity: 'rare', chancePercent: 2.9, weight: 290,
    fallbackImage: createArtwork('gift', 'Ice Cream', '#60a5fa', '#dbeafe'),
  },
  {
    kind: 'gift', label: 'Liberty Figure', name: 'Liberty Figure', model: 'liberty-figure', value: 335, unit: '⭐', icon: '🗽', rarity: 'rare', chancePercent: 2.7, weight: 270,
    fallbackImage: createArtwork('gift', 'Liberty', '#60a5fa', '#bfdbfe'),
  },
  {
    kind: 'gift', label: 'Desk Calendar', name: 'Desk Calendar', model: 'desk-calendar', value: 420, unit: '⭐', icon: '📅', rarity: 'rare', chancePercent: 2.1, weight: 210,
    fallbackImage: createArtwork('gift', 'Calendar', '#64748b', '#e2e8f0'),
  },
  {
    kind: 'gift', label: 'Big Year', name: 'Big Year', model: 'big-year', value: 290, unit: '⭐', icon: '🗓️', rarity: 'rare', chancePercent: 3.2, weight: 320,
    fallbackImage: createArtwork('gift', 'Big Year', '#0ea5e9', '#bae6fd'),
  },
  {
    kind: 'gift', label: 'Berry Box', name: 'Berry Box', model: 'berry-box', value: 670, unit: '⭐', icon: '🫐', rarity: 'epic', chancePercent: 1.5, weight: 150,
    fallbackImage: createArtwork('gift', 'Berry Box', '#8b5cf6', '#c4b5fd'),
  },
  {
    kind: 'gift', label: 'Eternal Rose', name: 'Eternal Rose', model: 'eternal-rose', value: 1946, unit: '⭐', icon: '🌹', rarity: 'legendary', chancePercent: 0.01, weight: 1,
    fallbackImage: createArtwork('gift', 'Eternal Rose', '#e11d48', '#fecdd3'),
  },
  {
    kind: 'gift', label: 'Bonded Ring', name: 'Bonded Ring', model: 'bonded-rind', value: 3768, unit: '⭐', icon: '🧩', rarity: 'mythic', chancePercent: 0.01, weight: 1,
    fallbackImage: createArtwork('gift', 'Bonded Ring', '#334155', '#cbd5e1'),
  },
];

const CASE600_DROP_TABLE = [
  {
    kind: 'stars', label: '200 звёзд', name: '200 звёзд', value: 200, unit: '⭐', icon: '⭐', rarity: 'common', chancePercent: 33.85, weight: 3385,
    image: createArtwork('stars', '200 звёзд', '#facc15', '#f97316'),
  },
  {
    kind: 'gift', label: 'Ginger Cookie', name: 'Ginger Cookie', model: 'ginger-cookie', value: 370, unit: '⭐', icon: '🍪', rarity: 'rare', chancePercent: 18.0, weight: 1800,
    fallbackImage: createArtwork('gift', 'Ginger Cookie', '#b45309', '#fed7aa'),
  },
  {
    kind: 'gift', label: 'Liberty Figure', name: 'Liberty Figure', model: 'liberty-figure', value: 335, unit: '⭐', icon: '🗽', rarity: 'rare', chancePercent: 15.0, weight: 1500,
    fallbackImage: createArtwork('gift', 'Liberty', '#60a5fa', '#bfdbfe'),
  },
  {
    kind: 'gift', label: 'Bunny Muffin', name: 'Bunny Muffin', model: 'bunny-mafin', value: 731, unit: '⭐', icon: '🐰', rarity: 'epic', chancePercent: 16.0, weight: 1600,
    fallbackImage: createArtwork('gift', 'Bunny Muffin', '#f472b6', '#fbcfe8'),
  },
  {
    kind: 'gift', label: 'Crystal Ball', name: 'Crystal Ball', model: 'crystal-ball', value: 1100, unit: '⭐', icon: '🔮', rarity: 'epic', chancePercent: 11.0, weight: 1100,
    fallbackImage: createArtwork('gift', 'Crystal Ball', '#a78bfa', '#ddd6fe'),
  },
  {
    kind: 'gift', label: 'Eternal Rose', name: 'Eternal Rose', model: 'eternal-rose', value: 1957, unit: '⭐', icon: '🌹', rarity: 'legendary', chancePercent: 6.1, weight: 610,
    fallbackImage: createArtwork('gift', 'Eternal Rose', '#e11d48', '#fecdd3'),
  },
  {
    kind: 'gift', label: 'Magic Potion', name: 'Magic Potion', model: 'magic-potion', value: 5500, unit: '⭐', icon: '🧪', rarity: 'mythic', chancePercent: 0.05, weight: 5,
    fallbackImage: createArtwork('gift', 'Magic Potion', '#0d9488', '#99f6e4'),
  },
  {
    kind: 'gift', label: 'Astral Shard', name: 'Astral Shard', model: 'astral-shard', value: 1059, unit: '⭐', icon: '✨', rarity: 'mythic', chancePercent: 0.0, weight: 0,
    fallbackImage: createArtwork('gift', 'Astral Shard', '#6366f1', '#c7d2fe'),
  },
];

[CASE150_DROP_TABLE, CASE250_DROP_TABLE, CASE400_DROP_TABLE, CASE600_DROP_TABLE].forEach(tbl => {
  tbl.forEach(item => {
    item.rarity = getRarityByStars(item.value);
  });
});

const GIFT_LIBRARY = [
  { label: 'Jingle Bells', name: 'Jingle Bells', value: 2.5, unit: 'GRAM', image: createArtwork('gift', 'Jingle Bells', '#8b5cf6', '#f59e0b') },
  { label: 'Santa Hat', name: 'Santa Hat', value: 3, unit: 'GRAM', image: createArtwork('gift', 'Santa Hat', '#f43f5e', '#fb923c') },
  { label: 'Homemade Cake', name: 'Homemade Cake', value: 3.5, unit: 'GRAM', image: createArtwork('gift', 'Homemade Cake', '#fda4af', '#facc15') },
  { label: 'Spiced Wine', name: 'Spiced Wine', value: 4, unit: 'GRAM', image: createArtwork('gift', 'Spiced Wine', '#b45309', '#fb923c') },
  { label: 'Jelly Bunny', name: 'Jelly Bunny', value: 5, unit: 'GRAM', image: createArtwork('gift', 'Jelly Bunny', '#fb7185', '#f9a8d4') },
  { label: 'Neon Heart', name: 'Neon Heart', value: 12, unit: 'GRAM', image: createArtwork('gift', 'Neon Heart', '#ec4899', '#22d3ee') },
  { label: 'Rose Bouquet', name: 'Rose Bouquet', value: 18, unit: 'GRAM', image: createArtwork('gift', 'Rose Bouquet', '#f472b6', '#fb7185') },
  { label: 'Diamond Ring', name: 'Diamond Ring', value: 25, unit: 'GRAM', image: createArtwork('gift', 'Diamond Ring', '#38bdf8', '#e0f2fe') },
  { label: 'Genie Lamp', name: 'Genie Lamp', value: 39, unit: 'GRAM', image: createArtwork('gift', 'Genie Lamp', '#a78bfa', '#34d399') },
  { label: 'Loot Bag', name: 'Loot Bag', value: 43.5, unit: 'GRAM', image: createArtwork('gift', 'Loot Bag', '#f59e0b', '#b45309') },
  { label: 'Magic Potion', name: 'Magic Potion', value: 55, unit: 'GRAM', image: createArtwork('gift', 'Magic Potion', '#14b8a6', '#7c3aed') },
  { label: 'Mini Oscar', name: 'Mini Oscar', value: 79, unit: 'GRAM', image: createArtwork('gift', 'Mini Oscar', '#facc15', '#f97316') },
  { label: 'Perfume Bottle', name: 'Perfume Bottle', value: 87, unit: 'GRAM', image: createArtwork('gift', 'Perfume Bottle', '#c084fc', '#fb7185') },
  { label: 'Astral Shard', name: 'Astral Shard', value: 89, unit: 'GRAM', image: createArtwork('gift', 'Astral Shard', '#60a5fa', '#a78bfa') },
  { label: 'Ion Gem', name: 'Ion Gem', value: 100, unit: 'GRAM', image: createArtwork('gift', 'Ion Gem', '#2dd4bf', '#0f766e') },
  { label: 'Precious Peach', name: 'Precious Peach', value: 320, unit: 'GRAM', image: createArtwork('gift', 'Precious Peach', '#fda4af', '#fb923c') },
  { label: "Durov's Cap", name: "Durov's Cap", value: 455, unit: 'GRAM', image: createArtwork('gift', "Durov's Cap", '#374151', '#f59e0b') },
  { label: 'Plush Pepe', name: 'Plush Pepe', value: 2500, unit: 'GRAM', image: createArtwork('gift', 'Plush Pepe', '#f472b6', '#7c3aed') },
];

const casinoUpgrades = {
  gift_wrap: { label: 'Украшение подарка', cost: 140, bonus: 0 },
  bonus_box: { label: 'Усиленный бокс', cost: 310, bonus: 40 },
  legendary_ribbon: { label: 'Легендарная лента', cost: 660, bonus: 120 },
};

function getStarPackages() {
  const packages = state.bootstrap?.pricing?.star_packages;
  if (packages && typeof packages === 'object') {
    return packages;
  }
  return { 50: 36.5, 100: 73, 150: 107.25, 200: 143, 250: 178.75, 500: 346 };
}

function calculateStarsEquivalentFromGram(gramValue) {
  const tonMarket = state.bootstrap?.pricing?.ton_market || {};
  const tonUsdt = Number(tonMarket.ton_usdt || 0);
  const giftValueUsdt = Number(gramValue || 0) * (tonUsdt || 0);
  if (!giftValueUsdt || !Number.isFinite(giftValueUsdt)) return 50;
  return Math.max(1, Math.round(giftValueUsdt * STARS_PER_USDT));
}

function getLiveGiftStarsPrice(item) {
  if (!item || item.kind !== 'gift') return Number(item?.value || 0);
  const model = String(item.model || '').trim().toLowerCase();
  if (!model) return Number(item.value || 0);
  const manual = state.bootstrap?.pricing?.nft_gift_prices || {};
  const quoted = Number(manual?.[model] || 0);
  if (Number.isFinite(quoted) && quoted > 0) {
    return Math.round(quoted);
  }
  return Number(item.value || 0);
}

function resolveGiftValue(item) {
  if (!item) return { kind: 'gift', label: 'NFT', value: 0, rarity: 'common' };
  if (item.kind === 'stars') {
    const label = item.label || item.name || `${fmt(item.value, 0)} звёзд`;
    return {
      ...item,
      label,
      rarity: getRarityByStars(item.value),
      image: item.image || item.fallbackImage || createArtwork('stars', label, '#ffd54f', '#ff8f00'),
      fallbackImage: item.fallbackImage || createArtwork('stars', label, '#ffd54f', '#ff8f00'),
    };
  }
  const nextValue = getLiveGiftStarsPrice(item);
  const model = String(item.model || '').trim().toLowerCase();
  const imageMap = state.bootstrap?.pricing?.nft_gift_images || {};
  const externalImage = String(imageMap?.[model] || '').trim();
  const useExternal = /^https?:\/\//i.test(externalImage);
  const label = item.label || item.name || 'NFT Gift';
  const fallback = item.fallbackImage || createArtwork('gift', label, '#8b5cf6', '#22d3ee', item.icon);
  return {
    ...item,
    value: nextValue,
    rarity: getRarityByStars(nextValue),
    image: useExternal ? externalImage : (item.image || fallback),
    fallbackImage: fallback,
  };
}

async function loadNftQuotes() {
  const manual = state.bootstrap?.pricing?.nft_gift_prices || {};
  state.nftQuotes = Object.keys(manual).reduce((acc, key) => {
    const value = Number(manual[key] || 0);
    if (Number.isFinite(value) && value > 0) {
      acc[key] = { stars_price: Math.round(value), source: 'admin_manual' };
    }
    return acc;
  }, {});
}

function getCaseReturnRate(tier) {
  const serverRate = state.bootstrap?.games?.config?.cases?.[tier]?.return_to_pay;
  const parsed = Number(serverRate);
  if (Number.isFinite(parsed) && parsed > 0) return parsed;
  const gameRtp = state.bootstrap?.pricing?.game_rtp_percent || {};
  if (tier === 'case150') {
    const v = Number(gameRtp.case150 || 0);
    if (Number.isFinite(v) && v > 0) return v / 100;
  }
  if (tier === 'case250') {
    const v = Number(gameRtp.case250 || 0);
    if (Number.isFinite(v) && v > 0) return v / 100;
  }
  if (tier === 'case400') {
    const v = Number(gameRtp.case400 || 0);
    if (Number.isFinite(v) && v > 0) return v / 100;
  }
  if (tier === 'case600') {
    const v = Number(gameRtp.case600 || 0);
    if (Number.isFinite(v) && v > 0) return v / 100;
  }
  const casesRtp = Number(gameRtp.cases || 0);
  if (Number.isFinite(casesRtp) && casesRtp > 0) return casesRtp / 100;
  if (tier === 'basic') return 0.76;
  if (tier === 'silver') return 0.71;
  return 0.64;
}

function buildGiftPool(tier) {
  if (tier === 'case150') {
    return CASE150_DROP_TABLE.map(item => resolveGiftValue(item));
  }
  if (tier === 'case250') {
    return CASE250_DROP_TABLE.map(item => resolveGiftValue(item));
  }
  if (tier === 'case400') {
    return CASE400_DROP_TABLE.map(item => resolveGiftValue(item));
  }
  if (tier === 'case600') {
    return CASE600_DROP_TABLE.map(item => resolveGiftValue(item));
  }

  const caseCfg = CASE_LIBRARY[tier] || { cost: 100 };
  const cost = Number(caseCfg.cost || 100);
  const returnRate = getCaseReturnRate(tier);
  const returnAmount = Math.round(cost * returnRate);
  const starItems = [
    { kind: 'stars', label: 'Пакет звёзд', name: 'Пакет звёзд', value: returnAmount, unit: '⭐', icon: '⭐', image: createArtwork('stars', 'Пакет звёзд', '#ffcf4d', '#ff6b35'), rarity: getRarityByStars(returnAmount), weight: 28 },
    { kind: 'stars', label: 'Кубок звёзд', name: 'Кубок звёзд', value: Math.round(cost * (returnRate + 0.08)), unit: '⭐', icon: '⭐', image: createArtwork('stars', 'Кубок звёзд', '#8b5cf6', '#22d3ee'), rarity: getRarityByStars(Math.round(cost * (returnRate + 0.08))), weight: 16 },
    { kind: 'stars', label: 'Сияние', name: 'Сияние', value: Math.round(cost * (returnRate + 0.16)), unit: '⭐', icon: '⭐', image: createArtwork('stars', 'Сияние', '#22d3ee', '#f472b6'), rarity: getRarityByStars(Math.round(cost * (returnRate + 0.16))), weight: 8 },
  ];

  const giftItems = GIFT_LIBRARY.filter((gift) => {
    // Exclude the PEPE plush gift from drops
    if ((gift.label || '').toLowerCase().includes('pepe') || (gift.name || '').toLowerCase().includes('пепе')) return false;
    const value = Number(gift.value || 0);
    if (tier === 'basic') return value <= 12;
    if (tier === 'silver') return value <= 100;
    return value >= 18;
  }).map((gift) => {
    const equivalentStars = calculateStarsEquivalentFromGram(Number(gift.value || 0));
    return {
      kind: 'gift',
      label: gift.label,
      name: gift.name,
      value: equivalentStars,
      baseValue: Number(gift.value || 0),
      unit: '⭐',
      icon: '🎁',
      image: gift.image,
      rarity: getRarityByStars(equivalentStars),
      weight: Math.max(3, Math.round((equivalentStars / Math.max(1, cost)) * 4)),
    };
  });

  return [...starItems, ...giftItems];
}

function pickCase150RewardByRtp(pool) {
  const gameRtp = state.bootstrap?.pricing?.game_rtp_percent || {};
  const rtpPercent = Number(gameRtp.case150 || 86);
  const adjustedRtp = Number.isFinite(rtpPercent) && rtpPercent > 0 ? rtpPercent : 86;

  const items = pool.map((item) => {
    const explicitChance = getItemChancePercent(item);
    const chance = explicitChance > 0 ? explicitChance : Number(item.weight || 1) / 100;
    const weight = Math.max(1, chance * 100 * (item.kind === 'stars' ? Math.max(0.1, adjustedRtp / 100) : 1));
    return {
      ...item,
      baseWeight: weight,
      rewardValue: Math.max(1, Number(item.value || 0)),
    };
  });

  const totalWeight = items.reduce((sum, item) => sum + item.baseWeight, 0);
  let roll = Math.random() * totalWeight;
  for (const item of items) {
    roll -= item.baseWeight;
    if (roll <= 0) return { ...item };
  }
  return { ...items[0] };
}

function pickGiftReward(tier) {
  const pool = buildGiftPool(tier);
  const gameRtp = state.bootstrap?.pricing?.game_rtp_percent || {};
  const caseRtpPercent = Number(gameRtp[tier] || gameRtp.cases || 86);
  const adjustedRtp = Number.isFinite(caseRtpPercent) && caseRtpPercent > 0 ? caseRtpPercent : 86;

  if (tier === 'case150') {
    return { ...pickCase150RewardByRtp(pool), tier };
  }

  const weightedPool = pool.map((item) => {
    const explicitChance = getItemChancePercent(item);
    const chance = explicitChance > 0 ? explicitChance : Number(item.weight || 1) / 100;
    const weight = Math.max(1, chance * 100 * (item.kind === 'stars' ? Math.max(0.1, adjustedRtp / 100) : 1));
    return { ...item, weight };
  });

  const totalWeight = weightedPool.reduce((sum, item) => sum + item.weight, 0);
  let roll = Math.random() * totalWeight;
  for (const item of weightedPool) {
    roll -= item.weight;
    if (roll <= 0) {
      return { ...item, tier };
    }
  }
  return { ...weightedPool[0], tier };
}

function updateCaseButtonsState() {
  const balance = Number(state.bootstrap?.profile?.balance_stars || 0);
  document.querySelectorAll('.case-open-btn').forEach((btn) => {
    const tier = btn.dataset.case;
    const cost = Number(CASE_LIBRARY[tier]?.cost || 0);
    const affordable = balance >= cost;
    btn.disabled = !affordable;
    btn.title = affordable ? '' : `Нужно ${fmt(cost, 0)} ⭐`;
    btn.classList.toggle('is-disabled', !affordable);
  });
}

function renderCaseConfigurations() {
  Object.entries(CASE_LIBRARY).forEach(([tier, cfg]) => {
    const card = document.querySelector(`.case-card[data-case="${tier}"]`);
    if (!card) return;
    const hint = card.querySelector('.case-meta .hint');
    if (hint) {
      hint.textContent = `${fmt(cfg.cost, 0)} ⭐ • ${fmt(cfg.minReward, 0)}–${fmt(cfg.maxReward, 0)} ⭐`;
    }
    const wheelInner = card.querySelector('.wheel-inner');
    if (wheelInner) {
      const items = buildGiftPool(tier).map(item => `
        <div class="case-roll-card ${item.kind === 'gift' ? 'nft' : ''}">
          <img class="case-roll-image" src="${getRewardImage(item)}" alt="${item.name || item.label}" onerror="this.onerror=null;this.src='${getRewardImageErrorFallback(item)}'" />
          <div class="case-roll-name">${item.name || item.label}</div>
          <div class="case-roll-value">${formatRewardValueLine(item)}</div>
        </div>
      `).join('');
      wheelInner.innerHTML = items;
    }
  });
  updateCaseButtonsState();
}

function buildWheelDisplayPool(tier, reward) {
  const pool = buildGiftPool(tier);
  const length = tier === 'case150' ? 48 : 20;
  const targetSlot = tier === 'case150' ? 40 : 16;
  const displayPool = [];

  for (let i = 0; i < length; i += 1) {
    const idx = Math.floor(Math.random() * pool.length);
    displayPool.push({ ...pool[idx] });
  }

  if (displayPool[targetSlot]) {
    displayPool[targetSlot] = { ...reward };
  }

  return { items: displayPool, targetSlot };
}

function renderWheelForReward(wheelInner, tier, reward) {
  if (!wheelInner) return;
  const display = buildWheelDisplayPool(tier, reward);
  const items = display.items.map((item, index) => `
    <div class="case-roll-card ${item.kind === 'gift' ? 'nft' : ''} ${index === display.targetSlot ? 'wheel-target' : ''}" data-wheel-target="${index === display.targetSlot}">
      <img class="case-roll-image" src="${getRewardImage(item)}" alt="${item.name || item.label}" onerror="this.onerror=null;this.src='${getRewardImageErrorFallback(item)}'" />
      <div class="case-roll-name">${item.name || item.label}</div>
      <div class="case-roll-value">${formatRewardValueLine(item)}</div>
    </div>
  `).join('');
  wheelInner.innerHTML = items;
}

function animateWheelToReward(wheelInner, tier, reward) {
  if (!wheelInner) return;
  renderWheelForReward(wheelInner, tier, reward);

  let shift = 0;
  const targetCard = wheelInner.querySelector('[data-wheel-target="true"]');
  if (targetCard && wheelInner.parentElement) {
    const containerWidth = wheelInner.parentElement.clientWidth || 320;
    const targetCenter = targetCard.offsetLeft + targetCard.offsetWidth / 2;
    const containerCenter = containerWidth / 2;
    shift = Math.max(0, targetCenter - containerCenter + 24);
  }

  wheelInner.style.transition = 'none';
  wheelInner.style.transform = 'translateX(0)';
  void wheelInner.offsetWidth;
  wheelInner.style.transition = 'transform 2200ms cubic-bezier(.2,.9,.2,1)';
  requestAnimationFrame(() => {
    wheelInner.style.transform = `translateX(-${shift}px)`;
  });
}

function renderInventory() {
  const wrap = $('inventoryList');
  if (!wrap) return;
  const inventory = Array.isArray(state.bootstrap?.inventory) ? state.bootstrap.inventory : [];
  if (!inventory.length) {
    wrap.innerHTML = '<div class="inventory-empty">Пока в инвентаре пусто — открывай кейсы и собирай редкие NFT.</div>';
    return;
  }
  wrap.innerHTML = inventory.map(item => `
    <article class="inventory-card">
      <div class="inventory-top">
        <div class="inventory-icon">
          ${item.kind === 'gift'
            ? `<img class="inventory-thumb" src="${getInventoryItemImage(item)}" alt="${item.name || item.label}" onerror="this.onerror=null;this.src='${getInventoryItemImageErrorFallback(item)}'" />`
            : item.icon}
        </div>
        <div>
          <div class="inventory-label">${item.name || item.label}</div>
          <div class="inventory-meta">${item.kind === 'stars' ? 'Звёздный подарок' : 'Подарок'} · ${getRarityByStars(getLiveGiftStarsPrice(item))}</div>
        </div>
      </div>
      <div class="inventory-value">${fmt(getLiveGiftStarsPrice(item), 0)} ⭐</div>
      <div class="actions">
        ${item.pending_withdraw ? '<span class="hint">Ожидайте подтверждения</span>' : `
          ${item.withdraw_rejected ? '<span class="hint">Заявка отклонена</span>' : ''}
          ${item.kind === 'gift' ? `<button class="primary tiny" data-upgrade-gift="${item.id}" style="background: linear-gradient(135deg, #7c3aed, #4f46e5);">⚡ Апгрейд</button>` : ''}
          <button class="primary tiny" data-sell-gift="${item.id}">Продать</button>
          ${item.withdraw_rejected ? '' : `<button class="ghost tiny" data-withdraw-gift="${item.id}">Вывести</button>`}
        `}
      </div>
    </article>
  `).join('');
  wrap.querySelectorAll('[data-upgrade-gift]').forEach(btn => btn.addEventListener('click', () => startUpgradeWithItem(btn.dataset.upgradeGift)));
  wrap.querySelectorAll('[data-sell-gift]').forEach(btn => btn.addEventListener('click', () => sellInventoryGift(btn.dataset.sellGift)));
  wrap.querySelectorAll('[data-withdraw-gift]').forEach(btn => btn.addEventListener('click', () => withdrawInventoryGift(btn.dataset.withdrawGift)));
}

async function sellInventoryGift(giftId) {
  try {
    const data = await api('/api/inventory/gift/sell', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, gift_id: giftId }),
    });
    state.bootstrap.profile = data.profile || state.bootstrap.profile;
    state.bootstrap.casino = data.casino || state.bootstrap.casino;
    state.bootstrap.inventory = Array.isArray(data.inventory) ? data.inventory : [];
    fillStats();
    renderCasino();
    renderInventory();
    toast(`${data?.converted?.label || 'Подарок'} продан за ${fmt(data?.converted?.stars_value || 0, 0)} ⭐`, 'success');
  } catch (err) {
    toast(err.message || 'Не удалось продать подарок', 'error');
  }
}

async function withdrawInventoryGift(giftId) {
  try {
    const data = await api('/api/inventory/gift/withdraw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, gift_id: giftId }),
    });
    state.bootstrap.inventory = Array.isArray(data.inventory) ? data.inventory : [];
    fillStats();
    renderInventory();
    toast('Заявка на вывод подарка отправлена', 'success');
  } catch (err) {
    toast(err.message || 'Не удалось отправить заявку', 'error');
  }
}

const $ = (id) => document.getElementById(id);
const fmt = (value, digits = 2) => Number(value || 0).toLocaleString('ru-RU', { maximumFractionDigits: digits });
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function toast(message, type = 'success') {
  let stack = document.getElementById('toastStack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toastStack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.textContent = message;
  stack.appendChild(node);
  setTimeout(() => node.remove(), 2800);
}

async function api(url, options = {}) {
  if (!state.initData) {
    enforceTelegramClient();
    throw new Error('Mini App доступен только внутри Telegram');
  }
  const init = { method: 'GET', ...options };
  const headers = new Headers(init.headers || {});
  if (state.initData && !headers.has('X-Telegram-Init-Data')) {
    headers.set('X-Telegram-Init-Data', state.initData);
  }
  if (init.body && typeof init.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  } else if (typeof FormData !== 'undefined' && init.body instanceof FormData) {
    headers.delete('Content-Type');
  }
  init.headers = headers;
  const response = await fetch(url, init);
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) {
    let message = data?.message || data?.detail || `${response.status} ${response.statusText}`;
    if (typeof message === 'object') {
      try {
        message = JSON.stringify(message);
      } catch (_) {
        message = String(message);
      }
    }
    if (response.status === 403 && typeof message === 'string' && message.includes('заблокирован')) {
      const bannedScreen = $('bannedScreen');
      if (bannedScreen) bannedScreen.classList.remove('hidden');
    }
    if ((response.status === 401 || response.status === 403) && typeof message === 'string' && message.includes('Telegram')) {
      enforceTelegramClient();
    }
    throw new Error(message);
  }
  return data;
}

function isMobileView() {
  return window.innerWidth <= 768;
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.dataset.panel === name);
  });

  if (name === 'tournaments') {
    loadTournaments().catch(e => console.error(e));
  }

  if (isMobileView()) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function initMobileScrollSpy() {
  // Sections now switch directly in mobile view.
}

let nftShopActiveRarity = 'all';
let nftShopSearchQuery = '';
let nftShopSortOrder = 'cheap';

function switchShopSubtab(tab) {
  const isStars = tab === 'stars';
  const starsBtn = $('shopSubtabStars');
  const nftBtn = $('shopSubtabNft');
  const starsView = $('shopStarsView');
  const nftView = $('shopNftView');

  if (starsBtn) starsBtn.classList.toggle('active', isStars);
  if (nftBtn) nftBtn.classList.toggle('active', !isStars);
  if (starsView) starsView.classList.toggle('hidden', !isStars);
  if (nftView) nftView.classList.toggle('hidden', isStars);

  if (!isStars) {
    renderNftShop();
  }
}

function setNftShopRarity(rarity) {
  nftShopActiveRarity = rarity || 'all';
  document.querySelectorAll('.nft-rarity-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.rarity === nftShopActiveRarity);
  });
  renderNftShop();
}

function onNftShopFilterChange() {
  const searchInput = $('nftShopSearch');
  const sortSelect = $('nftShopSort');
  if (searchInput) nftShopSearchQuery = (searchInput.value || '').trim().toLowerCase();
  if (sortSelect) nftShopSortOrder = sortSelect.value || 'cheap';
  renderNftShop();
}

function renderNftShop() {
  const grid = $('nftShopGrid');
  if (!grid) return;

  const hint = $('nftShopBalanceHint');
  const currentBalance = Number(state.bootstrap?.profile?.balance_stars || 0);
  if (hint) hint.textContent = `Баланс: ${fmt(currentBalance, 0)} ⭐`;

  let catalog = [];
  if (Array.isArray(state.bootstrap?.nft_shop_catalog) && state.bootstrap.nft_shop_catalog.length) {
    catalog = state.bootstrap.nft_shop_catalog.map(item => ({ ...item }));
  } else if (Array.isArray(state.bootstrap?.upgrade_targets) && state.bootstrap.upgrade_targets.length) {
    catalog = state.bootstrap.upgrade_targets.map(item => ({ ...item }));
  } else {
    const prices = state.bootstrap?.pricing?.nft_gift_prices || {};
    const images = state.bootstrap?.pricing?.nft_gift_images || {};
    catalog = Object.entries(prices).map(([model, price]) => ({
      kind: 'gift',
      model,
      name: model.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      label: model.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      value: Number(price || 0),
      image: String(images[model] || ''),
      rarity: 'common',
    }));
  }

  // Update with live prices and derive rarity from stars price
  catalog = catalog.map(item => {
    const liveVal = getLiveGiftStarsPrice(item);
    const val = liveVal > 0 ? liveVal : Number(item.value || 0);
    return {
      ...item,
      value: val,
      rarity: getRarityByStars(val),
    };
  });

  // Filter by search query
  if (nftShopSearchQuery) {
    catalog = catalog.filter(item => {
      const name = String(item.name || '').toLowerCase();
      const label = String(item.label || '').toLowerCase();
      const model = String(item.model || '').toLowerCase();
      return name.includes(nftShopSearchQuery) || label.includes(nftShopSearchQuery) || model.includes(nftShopSearchQuery);
    });
  }

  // Filter by rarity
  if (nftShopActiveRarity && nftShopActiveRarity !== 'all') {
    catalog = catalog.filter(item => getRarityByStars(item.value).toLowerCase() === nftShopActiveRarity.toLowerCase());
  }

  // Sort
  if (nftShopSortOrder === 'cheap') {
    catalog.sort((a, b) => (a.value || 0) - (b.value || 0));
  } else if (nftShopSortOrder === 'expensive') {
    catalog.sort((a, b) => (b.value || 0) - (a.value || 0));
  } else if (nftShopSortOrder === 'name') {
    catalog.sort((a, b) => String(a.name || a.label || '').localeCompare(String(b.name || b.label || ''), 'en'));
  }

  if (!catalog.length) {
    grid.innerHTML = '<div style="grid-column: 1 / -1; padding: 28px; text-align: center; color: #94a3b8;">Подарки не найдены. Попробуйте изменить фильтры.</div>';
    return;
  }

  grid.innerHTML = catalog.map(item => {
    const rarity = getRarityByStars(item.value);
    const price = Number(item.value || 0);
    const title = item.name || item.label || 'NFT Gift';
    const modelTag = item.model || 'Telegram Gift';
    return `
      <div class="nft-shop-card" data-model="${item.model}">
        <div class="nft-shop-card-badge rarity-${rarity}">${rarity}</div>
        <div class="nft-shop-card-img-wrap">
          <img class="nft-shop-card-img" src="${getInventoryItemImage(item)}" alt="${title}" onerror="this.onerror=null;this.src='${getInventoryItemImageErrorFallback(item)}'" />
        </div>
        <div class="nft-shop-card-title">${title}</div>
        <div class="nft-shop-card-model">${modelTag}</div>
        <div class="nft-shop-card-price-row">
          <span class="nft-shop-card-price">${fmt(price, 0)} ⭐</span>
        </div>
        <button type="button" class="primary nft-shop-buy-btn" data-buy-nft="${item.model}">
          Купить
        </button>
      </div>
    `;
  }).join('');

  grid.querySelectorAll('[data-buy-nft]').forEach(btn => {
    btn.addEventListener('click', () => buyNftShopGift(btn.dataset.buyNft));
  });
}

async function buyNftShopGift(model) {
  if (!model) return;
  const catalog = state.bootstrap?.nft_shop_catalog || state.bootstrap?.upgrade_targets || [];
  const gift = catalog.find(x => x.model === model) || { model, label: model, value: getLiveGiftStarsPrice({ kind: 'gift', model }) };
  const price = getLiveGiftStarsPrice(gift) || Number(gift.value || 0);
  const currentBalance = Number(state.bootstrap?.profile?.balance_stars || 0);

  if (currentBalance < price) {
    toast(`Недостаточно звёзд. Нужно ${fmt(price, 0)} ⭐, ваш баланс: ${fmt(currentBalance, 0)} ⭐`, 'error');
    return;
  }

  const confirmed = confirm(`Купить подарок "${gift.name || gift.label}" за ${fmt(price, 0)} ⭐?\nПодарок поступит в ваш инвентарь.`);
  if (!confirmed) return;

  try {
    const data = await api('/api/shop/nft/buy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, model }),
    });

    state.bootstrap.profile = data.profile || state.bootstrap.profile;
    state.bootstrap.inventory = Array.isArray(data.inventory) ? data.inventory : [];
    fillStats();
    renderCasino();
    renderInventory();
    renderNftShop();
    toast(`🎉 Подарок "${gift.name || gift.label}" успешно куплен и добавлен в инвентарь!`, 'success');
  } catch (err) {
    toast(err.message || 'Ошибка покупки подарка', 'error');
  }
}

function switchAdminTab(name) {
  const panels = [...document.querySelectorAll('.admin-subpanel')];
  if (!panels.some(panel => panel.dataset.adminPanel === name)) return;
  document.querySelectorAll('.admin-subtab').forEach(btn => {
    const selected = btn.dataset.adminTab === name;
    btn.classList.toggle('active', selected);
    btn.setAttribute('aria-selected', String(selected));
  });
  panels.forEach(panel => {
    const selected = panel.dataset.adminPanel === name;
    panel.hidden = !selected;
    panel.classList.toggle('active', selected);
  });

  if (name === 'tournaments') {
    loadAdminTournaments().catch(e => console.error(e));
    setTimeout(initAdminTournGamesGrid, 20);
  }
  if (name === 'shifts') {
    loadAdminShiftsState().catch(e => console.error(e));
  }
}

function handleTopupStars(e) {
  if (e && e.preventDefault) e.preventDefault();
  switchTab('shop');
  setTimeout(() => {
    const el = document.getElementById('starsAmount') || document.getElementById('shopStarsCard');
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('starsAmount')?.focus();
  }, 100);
}

function handleTopupTon(e) {
  if (e && e.preventDefault) e.preventDefault();
  switchTab('shop');
  setTimeout(() => {
    const el = document.getElementById('tonAmount') || document.getElementById('shopTonCard');
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('tonAmount')?.focus();
  }, 100);
}

window.switchTab = switchTab;
window.switchAdminTab = switchAdminTab;
window.handleTopupStars = handleTopupStars;
window.handleTopupTon = handleTopupTon;

function fillStats() {
  const profile = state.bootstrap?.profile || {};
  const user = state.bootstrap?.user || {};
  $('starsBalance').textContent = fmt(profile.balance_stars, 2);
  $('tonBalance').textContent = fmt(profile.balance_ton, 4);
  $('totalBought').textContent = fmt(profile.total_stars, 0);
  $('helloText').textContent = `Привет, ${user.first_name || user.username || 'друг'}! Mini App синхронизирован с ботом.`;
  const packageKeys = Object.keys(getStarPackages()).map(Number).sort((a, b) => a - b);
  const packageHint = packageKeys.length ? packageKeys.join(', ') : '—';
  $('starsRateHint').textContent = `Пакеты: ${packageHint}`;
  $('reviewsChannelHint').textContent = state.bootstrap?.constants?.reviews_channel || 'канал отзывов';
}

function renderHistory() {
  const list = $('historyList');
  const items = state.bootstrap?.transactions || [];
  if (!items.length) {
    list.className = 'stack-list empty-state';
    list.textContent = 'Пока пусто.';
    return;
  }
  list.className = 'stack-list';
  list.innerHTML = items.map(item => {
    const title = item.type === 'stars' ? `${item.stars || 0} ⭐` : item.type === 'premium' ? `Premium ${item.months || 0} мес.` : item.type === 'ton_topup' ? `Пополнение ${fmt(item.ton_amount, 4)} TON` : item.type === 'withdraw_ton' ? `Вывод ${fmt(item.ton_amount, 4)} TON` : `Вывод ${item.stars || 0} ⭐`;
    return `<div class="item-card"><div class="item-row"><strong>#${escapeHtml(String(item.id))} · ${escapeHtml(title)}</strong><span class="badge ${escapeHtml(item.status || 'pending')}">${escapeHtml(item.status || 'pending')}</span></div><div class="hint">${escapeHtml(item.date || '—')}</div><div class="hint">Оплата: ${escapeHtml(item.payment_method || '—')}</div></div>`;
  }).join('');
}

function renderReviews() {
  const list = $('reviewsList');
  const items = state.bootstrap?.reviews || [];
  if (!items.length) {
    list.className = 'stack-list empty-state';
    list.textContent = 'Пока нет отзывов.';
    return;
  }
  list.className = 'stack-list';
  list.innerHTML = items.map(item => `<div class="item-card"><div class="item-row"><strong>@${escapeHtml(item.username || 'user')}</strong><span class="hint">${escapeHtml(item.date || '—')}</span></div><div>${escapeHtml(item.text || '')}</div></div>`).join('');
}

function renderGameStats() {
  const wrap = $('gameStats');
  if (!wrap) return;
  const games = state.bootstrap?.games || {};
  const blocks = [
    ['Мины', games.mines?.user, games.mines?.global],
    ['Crash', games.crash?.user, games.crash?.global],
    ['Рулетка', games.roulette?.user, games.roulette?.global],
    ['Монетка', games.coin?.user, games.coin?.global],
  ];
  wrap.innerHTML = blocks.map(([name, user, global]) => `
    <div class="stat-box">
      <strong>${name}</strong>
      <div class="hint">Лично: ${fmt(user?.games_played || 0, 0)} игр · ${fmt(user?.wins || 0, 0)} побед</div>
      <div class="hint">Поставлено: ${fmt(user?.total_bet || 0)}</div>
      <div class="hint">Выиграно: ${fmt(user?.total_won || 0)}</div>
      <div class="hint">Общий профит бота: ${fmt(global?.net_profit || 0)}</div>
    </div>
  `).join('');
}

function renderCasino() {
  const casino = state.bootstrap?.casino || { cases: {}, upgrades: {}, last_case: null, last_upgrade: null };
  const updateText = (id, text) => {
    const el = $(id);
    if (el) el.textContent = text;
  };
  updateText('basicCaseCount', casino.cases?.basic || 0);
  updateText('silverCaseCount', casino.cases?.silver || 0);
  updateText('goldCaseCount', casino.cases?.gold || 0);
  updateText('case150CaseCount', casino.cases?.case150 || 0);
  updateText('case250CaseCount', casino.cases?.case250 || 0);
  updateText('case400CaseCount', casino.cases?.case400 || 0);
  updateText('case600CaseCount', casino.cases?.case600 || 0);
  updateText('giftWrapCount', casino.upgrades?.gift_wrap || 0);
  updateText('bonusBoxCount', casino.upgrades?.bonus_box || 0);
  updateText('legendaryRibbonCount', casino.upgrades?.legendary_ribbon || 0);
  updateText('caseResult', casino.last_case?.description || 'Открой кейс и получи награду.');
  updateText('upgradeResult', casino.last_upgrade
    ? `Куплен ${casino.last_upgrade.label}${casino.last_upgrade.bonus_stars ? `, бонус ${fmt(casino.last_upgrade.bonus_stars, 0)} ⭐` : ''}.`
    : 'Покупай апгрейды и получай подарочные плюшки.');
  renderInventory();
}

function isAdmin() {
  return Boolean(state.bootstrap?.is_admin);
}

function setAdminTabVisibility() {
  const tab = $('adminTabBtn');
  if (!tab) return;
  tab.classList.toggle('hidden', !isAdmin());
  if (!isAdmin() && document.querySelector('.tab-panel.active')?.dataset?.panel === 'admin') {
    switchTab('shop');
  }
}

function renderAdminSummary(summary) {
  const node = $('adminSummary');
  if (!node) return;
  if (!summary) {
    node.textContent = 'Нет данных.';
    return;
  }
  node.textContent = [
    `Пользователи: ${fmt(summary.users_total || 0, 0)}`,
    `Заказы: ${fmt(summary.orders_total || 0, 0)} (подтверждено: ${fmt(summary.orders_confirmed || 0, 0)})`,
    `Оборот: ${fmt(summary.total_earned_uah || 0)} грн`,
    `Продано stars: ${fmt(summary.stars_sold || 0, 0)} ⭐`,
    `Висящих заявок: ${fmt(summary.orders_pending || 0, 0)}`,
    `Pending предложений: ${fmt(summary.suggestions_pending || 0, 0)}`,
  ].join('\n');
}

function renderAdminPromocodes(items) {
  const wrap = $('adminPromocodes');
  if (!wrap) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    wrap.className = 'stack-list empty-state';
    wrap.textContent = 'Список промокодов пуст.';
    return;
  }
  wrap.className = 'stack-list';
  wrap.innerHTML = list.map((item) => {
    const used = Number(item.used_count || 0);
    const max = Number(item.max_uses || 0);
    return `<div class="item-card"><div class="item-row"><strong>${escapeHtml(item.code || '')}</strong><span class="badge ${item.active ? 'confirmed' : 'cancelled'}">${item.active ? 'active' : 'inactive'}</span></div><div class="hint">Использовано ${used}/${max} · ${fmt(item.amount_stars || 0, 0)} ⭐</div></div>`;
  }).join('');
}

function renderAdminSuggestions(items) {
  const wrap = $('adminSuggestions');
  if (!wrap) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    wrap.className = 'stack-list empty-state';
    wrap.textContent = 'Нет предложений.';
    return;
  }
  wrap.className = 'stack-list';
  wrap.innerHTML = list.map((item) => {
    const status = String(item.status || 'pending');
    return `
      <div class="item-card">
        <div class="item-row"><strong>#${escapeHtml(String(item.id))} @${escapeHtml(item.username || 'user')}</strong><span class="badge ${escapeHtml(status)}">${escapeHtml(status)}</span></div>
        <div>${escapeHtml(item.text || '')}</div>
        <div class="actions">
          <button data-suggestion-act="under_review" data-suggestion-id="${escapeHtml(String(item.id))}">В работу</button>
          <button data-suggestion-act="rejected" data-suggestion-id="${escapeHtml(String(item.id))}">Отклонить</button>
        </div>
      </div>
    `;
  }).join('');

  wrap.querySelectorAll('[data-suggestion-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const suggestionId = Number(btn.dataset.suggestionId || 0);
      const action = btn.dataset.suggestionAct;
      try {
        await api('/api/admin/suggestions/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ init_data: state.initData, suggestion_id: suggestionId, action }),
        });
        toast('Статус предложения обновлён');
        await loadAdminDashboard();
      } catch (err) {
        toast(err.message, 'error');
      }
    });
  });
}

function renderAdminUnsubs(items) {
  const wrap = $('adminUnsubs');
  if (!wrap) return;
  const list = Array.isArray(items) ? items : [];
  if (!list.length) {
    wrap.className = 'stack-list empty-state';
    wrap.textContent = 'Логи пусты.';
    return;
  }
  wrap.className = 'stack-list';
  wrap.innerHTML = list.map((item) => `<div class="item-card"><div class="item-row"><strong>${escapeHtml(String(item.username || item.user_id || 'user'))}</strong><span class="hint">${escapeHtml(item.date || '—')}</span></div><div class="hint">${escapeHtml(item.reason || item.action || 'unsubscribe')}</div></div>`).join('');
}

function filterAdminNftPrices() {
  const q = ($('adminNftPriceSearch')?.value || '').trim().toLowerCase();
  document.querySelectorAll('#adminNftPriceList label').forEach(label => {
    const model = label.querySelector('input')?.dataset.nftModel || '';
    const text = label.textContent.toLowerCase();
    const match = !q || text.includes(q) || model.toLowerCase().includes(q);
    label.style.display = match ? '' : 'none';
  });
}

function filterAdminNftImages() {
  const q = ($('adminNftImageSearch')?.value || '').trim().toLowerCase();
  document.querySelectorAll('#adminNftImageList label').forEach(label => {
    const model = label.querySelector('input')?.dataset.nftImageModel || '';
    const text = label.textContent.toLowerCase();
    const match = !q || text.includes(q) || model.toLowerCase().includes(q);
    label.style.display = match ? '' : 'none';
  });
}

async function adminAddNewNftGift() {
  const modelInput = $('adminNewNftModel');
  const priceInput = $('adminNewNftPrice');
  const imageInput = $('adminNewNftImage');

  const model = (modelInput?.value || '').trim().toLowerCase();
  const price = Number(priceInput?.value || 0);
  const imageUrl = (imageInput?.value || '').trim();

  if (!model) {
    toast('Введите идентификатор (model) подарка', 'error');
    return;
  }
  if (!price || price <= 0) {
    toast('Введите корректную цену в звёздах', 'error');
    return;
  }

  try {
    const data = await api('/api/admin/prices/nft/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, model, price, image_url: imageUrl }),
    });

    if (state.bootstrap?.pricing) {
      state.bootstrap.pricing.nft_gift_prices = data.prices || state.bootstrap.pricing.nft_gift_prices;
      state.bootstrap.pricing.nft_gift_images = data.images || state.bootstrap.pricing.nft_gift_images;
    }
    if (data.catalog) {
      state.bootstrap.nft_shop_catalog = data.catalog;
    }

    renderAdminNftPriceInputs(data.prices);
    renderAdminNftImageInputs(data.images);
    renderNftShop();

    if (modelInput) modelInput.value = '';
    if (priceInput) priceInput.value = '500';
    if (imageInput) imageInput.value = '';

    toast(`Подарок "${model}" успешно добавлен в магазин!`, 'success');
  } catch (err) {
    toast(err.message || 'Ошибка добавления подарка', 'error');
  }
}

function renderAdminNftPriceInputs(prices) {
  const wrap = $('adminNftPriceList');
  if (!wrap) return;
  const map = prices || state.bootstrap?.pricing?.nft_gift_prices || {};
  const entries = Object.entries(map);
  wrap.innerHTML = entries.map(([model, price]) => `
    <label>${model}
      <input type="number" min="1" step="1" data-nft-model="${model}" value="${Number(price || 0)}" />
    </label>
  `).join('');
  filterAdminNftPrices();
}

function renderAdminNftImageInputs(images) {
  const wrap = $('adminNftImageList');
  if (!wrap) return;
  const imageMap = images || state.bootstrap?.pricing?.nft_gift_images || {};
  const priceMap = state.bootstrap?.pricing?.nft_gift_prices || {};
  const models = Object.keys(priceMap).length ? Object.keys(priceMap) : Object.keys(imageMap);
  wrap.innerHTML = models.map((model) => `
    <label>${model}
      <input type="text" data-nft-image-model="${model}" value="${String(imageMap[model] || '')}" placeholder="https://..." />
    </label>
  `).join('');
  filterAdminNftImages();
}

const DEFAULT_CASE_DEFS = {
  case150: {
    label: "Летний кейс (150⭐️)",
    cost: 150,
    items: [
      { id: "stars_25", label: "25 звёзд", icon: "⭐", value: 25, rarity: "common", default_chance: 73.86 },
      { id: "lush-bouquet", label: "Lush Bouquet", icon: "💐", value: 517, rarity: "rare", default_chance: 4.0 },
      { id: "pool-float", label: "Pool Float", icon: "🦒", value: 375, rarity: "common", default_chance: 4.0 },
      { id: "instant-ramen", label: "Instant Ramen", icon: "🍜", value: 337, rarity: "common", default_chance: 5.0 },
      { id: "ice-cream", label: "Ice Cream", icon: "🍦", value: 370, rarity: "common", default_chance: 5.64 },
      { id: "ufc-box", label: "UFC Strike", icon: "🥊", value: 1200, rarity: "epic", default_chance: 3.0 },
      { id: "stellar-rocket", label: "Stellar Rocket", icon: "🚀", value: 1100, rarity: "epic", default_chance: 2.0 },
      { id: "chester-hat", label: "Jester Hat", icon: "🎩", value: 950, rarity: "rare", default_chance: 2.5 }
    ]
  },
  case250: {
    label: "Завоз (250⭐️)",
    cost: 250,
    items: [
      { id: "stars_25", label: "25 звёзд", icon: "⭐", value: 25, rarity: "common", default_chance: 43.79 },
      { id: "stars_75", label: "75 звёзд", icon: "⭐", value: 75, rarity: "common", default_chance: 43.79 },
      { id: "ice-cream", label: "Ice Cream", icon: "🍦", value: 370, rarity: "common", default_chance: 2.9 },
      { id: "liberty-figure", label: "Statue of Liberty", icon: "🗽", value: 335, rarity: "common", default_chance: 2.7 },
      { id: "desk-calendar", label: "Desk Calendar", icon: "📅", value: 420, rarity: "common", default_chance: 2.1 },
      { id: "big-year", label: "Big Year", icon: "🗓️", value: 290, rarity: "common", default_chance: 3.2 },
      { id: "berry-box", label: "Berry Box", icon: "🫐", value: 670, rarity: "rare", default_chance: 1.5 },
      { id: "eternal-rose", label: "Eternal Rose", icon: "🌹", value: 1957, rarity: "legendary", default_chance: 0.01 },
      { id: "bonded-rind", label: "Bonded Ring", icon: "🧩", value: 3768, rarity: "legendary", default_chance: 0.01 }
    ]
  },
  case400: {
    label: "Богатый (400⭐️)",
    cost: 400,
    items: [
      { id: "stars_50", label: "50 звёзд", icon: "⭐", value: 50, rarity: "common", default_chance: 25.1 },
      { id: "stars_100", label: "100 звёзд", icon: "⭐", value: 100, rarity: "common", default_chance: 25.1 },
      { id: "candy-cane", label: "Candy Cane", icon: "🍬", value: 370, rarity: "common", default_chance: 14.9 },
      { id: "liberty-figure", label: "Statue of Liberty", icon: "🗽", value: 335, rarity: "common", default_chance: 16.3 },
      { id: "love-candle", label: "Love Candle", icon: "🕯️", value: 731, rarity: "rare", default_chance: 8.2 },
      { id: "crystal-ball", label: "Crystal Ball", icon: "🔮", value: 1100, rarity: "epic", default_chance: 5.3 },
      { id: "flying-broom", label: "Flying Broom", icon: "🧹", value: 1057, rarity: "epic", default_chance: 4.9 },
      { id: "genie-lamp", label: "Genie Lamp", icon: "🪔", value: 2200, rarity: "legendary", default_chance: 0.2 },
      { id: "loot-bag", label: "Loot Bag", icon: "👜", value: 3768, rarity: "legendary", default_chance: 0.0 }
    ]
  },
  case600: {
    label: "Лакшери (600⭐️)",
    cost: 600,
    items: [
      { id: "stars_200", label: "200 звёзд", icon: "⭐", value: 200, rarity: "common", default_chance: 33.85 },
      { id: "ginger-cookie", label: "Ginger Cookie", icon: "🍪", value: 370, rarity: "common", default_chance: 18.0 },
      { id: "liberty-figure", label: "Statue of Liberty", icon: "🗽", value: 335, rarity: "common", default_chance: 15.0 },
      { id: "bunny-mafin", label: "Bunny Muffin", icon: "🐰", value: 731, rarity: "rare", default_chance: 16.0 },
      { id: "crystal-ball", label: "Crystal Ball", icon: "🔮", value: 1100, rarity: "epic", default_chance: 11.0 },
      { id: "eternal-rose", label: "Eternal Rose", icon: "🌹", value: 1957, rarity: "legendary", default_chance: 6.1 },
      { id: "magic-potion", label: "Magic Potion", icon: "🧪", value: 5500, rarity: "mythic", default_chance: 0.05 },
      { id: "astral-shard", label: "Astral Shard", icon: "✨", value: 1059, rarity: "epic", default_chance: 0.0 }
    ]
  }
};

window.recalcAdminCaseTierTotal = function(tier) {
  let sum = 0;
  document.querySelectorAll(`input[data-case-tier="${tier}"]`).forEach((inp) => {
    sum += Number(inp.value || 0);
  });
  const el = document.getElementById(`caseTotal_${tier}`);
  if (el) {
    el.textContent = `${sum.toFixed(2)}%`;
    el.style.color = Math.abs(sum - 100) < 0.05 ? '#4ade80' : 'rgba(255,255,255,0.9)';
  }
};

function renderAdminNftCaseChancesInputs(chances) {
  const wrap = $('adminNftCaseChancesList');
  if (!wrap) return;
  const caseDefs = state.bootstrap?.pricing?.case_definitions || DEFAULT_CASE_DEFS;
  const savedChances = chances || state.bootstrap?.pricing?.case_chances || {};

  const html = Object.entries(caseDefs).map(([tier, cdef]) => {
    const tierSaved = savedChances[tier] || {};
    const items = cdef.items || [];
    let tierTotal = 0;

    const itemsHtml = items.map((item) => {
      const currentVal = tierSaved[item.id] !== undefined ? tierSaved[item.id] : item.default_chance;
      const valNum = Number(currentVal !== undefined ? currentVal : (item.chance_percent || 0));
      tierTotal += valNum;
      const rarityLabel = {
        common: 'Обычный',
        rare: 'Редкий',
        epic: 'Эпический',
        legendary: 'Легендарный',
        mythic: 'Мифический',
      }[item.rarity] || item.rarity;

      return `
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:6px 10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
          <div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;">
            <span style="font-size:18px;">${item.icon || '🎁'}</span>
            <div style="min-width:0;">
              <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.label || item.name}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.45);">${item.value ? item.value + ' ⭐ · ' : ''}${rarityLabel}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
            <input type="number" min="0" max="100" step="0.01"
              data-case-tier="${tier}"
              data-case-item-id="${item.id}"
              data-nft-case-chance-model="${item.model || item.id}"
              value="${valNum}"
              placeholder="0.00"
              style="width:80px;text-align:right;padding:4px 6px;font-size:13px;"
              oninput="recalcAdminCaseTierTotal('${tier}')"
            />
            <span style="font-size:12px;color:rgba(255,255,255,0.6);">%</span>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="cardish" style="padding:14px;border:1px solid rgba(255,255,255,0.08);border-radius:12px;background:rgba(255,255,255,0.02);margin-bottom:12px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
          <div>
            <h3 style="margin:0;font-size:15px;display:flex;align-items:center;gap:6px;">
              <span>📦</span> ${cdef.label || tier}
            </h3>
            <span style="font-size:12px;color:rgba(255,255,255,0.5);">Цена открытия: <b>${cdef.cost || 0} ⭐</b></span>
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,0.6);text-align:right;">
            Сумма: <b id="caseTotal_${tier}">${tierTotal.toFixed(2)}%</b>
          </div>
        </div>
        <div class="inline-grid compact-2" style="gap:8px;">
          ${itemsHtml}
        </div>
      </div>
    `;
  }).join('');

  wrap.innerHTML = html;
}

function renderAdminDashboard() {
  const dash = state.adminDashboard || {};
  renderAdminSummary(dash.summary);
  renderAdminSuggestions(dash.suggestions || []);
  renderAdminPromocodes(dash.promocodes || []);
  renderAdminUnsubs(dash.unsubs || []);
  if ($('adminStarPackagesJson')) {
    $('adminStarPackagesJson').value = JSON.stringify(dash.prices?.star_packages || state.bootstrap?.pricing?.star_packages || {}, null, 2);
  }
  if ($('adminPremiumJson')) {
    $('adminPremiumJson').value = JSON.stringify(dash.prices?.premium_prices || state.bootstrap?.pricing?.premium_prices || {}, null, 2);
  }
  const gameRtp = dash.prices?.game_rtp_percent || state.bootstrap?.pricing?.game_rtp_percent || {};
  if ($('adminRtpMines')) $('adminRtpMines').value = Number(gameRtp.mines || 95);
  if ($('adminRtpCrash')) $('adminRtpCrash').value = Number(gameRtp.crash || 95);
  if ($('adminRtpRoulette')) $('adminRtpRoulette').value = Number(gameRtp.roulette || 95);
  if ($('adminRtpCases')) $('adminRtpCases').value = Number(gameRtp.cases || 86);
  if ($('adminRtpCase150')) $('adminRtpCase150').value = Number(gameRtp.case150 || 86);
  if ($('adminRtpCase250')) $('adminRtpCase250').value = Number(gameRtp.case250 || 88);
  if ($('adminRtpCase400')) $('adminRtpCase400').value = Number(gameRtp.case400 || 90);
  if ($('adminRtpCase600')) $('adminRtpCase600').value = Number(gameRtp.case600 || 92);
  if ($('adminRtpUpgrade')) $('adminRtpUpgrade').value = Number(gameRtp.upgrade || 95);
  const coinSettings = dash.prices?.coin_game_settings || state.bootstrap?.pricing?.coin_game_settings || {};
  if ($('adminCoinMinBet')) $('adminCoinMinBet').value = Number(coinSettings.min_bet || 5);
  if ($('adminCoinMaxBet')) $('adminCoinMaxBet').value = Number(coinSettings.max_bet || 10000);
  if ($('adminCoinOddsEagle')) $('adminCoinOddsEagle').value = Number(coinSettings.odds?.eagle || 45);
  if ($('adminCoinOddsTails')) $('adminCoinOddsTails').value = Number(coinSettings.odds?.tails || 45);
  if ($('adminCoinOddsEdge')) $('adminCoinOddsEdge').value = Number(coinSettings.odds?.edge || 10);
  if ($('adminCoinMulEagle')) $('adminCoinMulEagle').value = Number(coinSettings.multipliers?.eagle || 2);
  if ($('adminCoinMulTails')) $('adminCoinMulTails').value = Number(coinSettings.multipliers?.tails || 2);
  if ($('adminCoinMulEdge')) $('adminCoinMulEdge').value = Number(coinSettings.multipliers?.edge || 5);
  renderAdminNftPriceInputs(dash.prices?.nft_gift_prices || state.bootstrap?.pricing?.nft_gift_prices || {});
  renderAdminNftImageInputs(dash.prices?.nft_gift_images || state.bootstrap?.pricing?.nft_gift_images || {});
  renderAdminNftCaseChancesInputs(dash.prices?.case_chances || state.bootstrap?.pricing?.case_chances || dash.prices?.nft_case_chances || {});
}

async function loadAdminDashboard() {
  if (!isAdmin()) return;
  const data = await api('/api/admin/dashboard');
  state.adminDashboard = data;
  if (!state.bootstrap.pricing) state.bootstrap.pricing = {};
  if (data?.prices) {
    state.bootstrap.pricing.star_packages = data.prices.star_packages || state.bootstrap.pricing.star_packages;
    state.bootstrap.pricing.premium_prices = data.prices.premium_prices || state.bootstrap.pricing.premium_prices;
    state.bootstrap.pricing.nft_gift_prices = data.prices.nft_gift_prices || state.bootstrap.pricing.nft_gift_prices;
    state.bootstrap.pricing.nft_gift_images = data.prices.nft_gift_images || state.bootstrap.pricing.nft_gift_images;
    state.bootstrap.pricing.nft_case_chances = data.prices.nft_case_chances || state.bootstrap.pricing.nft_case_chances;
    state.bootstrap.pricing.case_chances = data.prices.case_chances || state.bootstrap.pricing.case_chances;
    state.bootstrap.pricing.case_definitions = data.prices.case_definitions || state.bootstrap.pricing.case_definitions;
    state.bootstrap.pricing.game_rtp_percent = data.prices.game_rtp_percent || state.bootstrap.pricing.game_rtp_percent;
    state.bootstrap.pricing.coin_game_settings = data.prices.coin_game_settings || state.bootstrap.pricing.coin_game_settings;
  }
  await loadNftQuotes();
  renderCaseConfigurations();
  renderInventory();
  renderAdminDashboard();
}
 
function updateCrashGraph(history = []) {
  const line = $('crashLine');
  if (!line) return;
  const maxPoints = history.length - 1;
  const height = 70;
  const points = history.map((value, idx) => {
    const progress = maxPoints > 0 ? idx / maxPoints : 0;
    const x = progress * 52;
    const y = height - 8 - progress ** 2 * (height - 18);
    return `${x},${y}`;
  });
  line.setAttribute('points', points.length ? points.join(' ') : '0,70');

  const rocket = $('crashRocket');
  if (rocket && history.length) {
    const lastPoint = points[points.length - 1].split(',').map(Number);
    rocket.style.left = `${lastPoint[0]}%`;
    rocket.style.top = `${(lastPoint[1] / height) * 100}%`;
  }
}

function spawnCrashCoefficient(value) {
  const stream = $('crashMultiplierStream');
  const stage = document.querySelector('.crash-stage');
  if (!stream || !stage) return;

  const chip = document.createElement('span');
  chip.className = 'crash-coefficient';
  chip.textContent = `${fmt(value, 2)}x`;
  chip.style.setProperty('--chip-flight-distance', `${Math.round(stage.clientWidth * 0.76)}px`);
  chip.style.top = `${Math.max(46, 74 - Math.log(Math.max(value, 1)) * 9)}%`;
  chip.addEventListener('animationend', () => chip.remove(), { once: true });
  stream.appendChild(chip);

  while (stream.children.length > 8) stream.firstElementChild?.remove();
}

function updateCrashActionButtons(active) {
  const playBtn = $('crashPlayBtn');
  const cashoutBtn = $('crashCashoutBtn');
  if (!playBtn || !cashoutBtn) return;
  playBtn.style.display = active ? 'none' : 'block';
  cashoutBtn.style.display = active ? 'block' : 'none';
  cashoutBtn.disabled = !active;
}

async function openCase(tier) {
  if (state.caseOpening) return;
  const btn = document.querySelector(`.case-open-btn[data-case="${tier}"]`);
  const card = document.querySelector(`.case-card[data-case="${tier}"]`);
  const cost = Number(CASE_LIBRARY[tier]?.cost || 0);
  const wheelInner = card ? card.querySelector('.wheel-inner') : null;
  const resultEl = document.getElementById(`${tier}CaseResult`);

  if (!state.bootstrap?.profile) state.bootstrap.profile = { balance_stars: 0, total_stars: 0 };
  const currentBalance = Number(state.bootstrap.profile.balance_stars || 0);
  if (currentBalance < cost) {
    if (resultEl) resultEl.textContent = `Недостаточно звёзд. Нужно ${fmt(cost, 0)} ⭐`;
    throw new Error(`Недостаточно звёзд. Нужно ${fmt(cost, 0)} ⭐`);
  }

  state.caseOpening = true;
  if (btn) btn.disabled = true;
  try {
    if (resultEl) resultEl.textContent = 'Открываем кейс...';
    const data = await api('/api/casino/case/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, tier }),
    });
    const reward = resolveGiftValue(data?.case?.reward_item || {
      kind: 'stars',
      label: `${fmt(Number(data?.case?.reward || 0), 0)} звёзд`,
      value: Number(data?.case?.reward || 0),
      unit: '⭐',
      icon: '⭐',
      rarity: 'common',
    });

    if (wheelInner) {
      animateWheelToReward(wheelInner, tier, reward);
    }
    await sleep(2200);

    state.bootstrap.profile = data.profile || state.bootstrap.profile;
    state.bootstrap.casino = data.casino || state.bootstrap.casino;
    state.bootstrap.inventory = Array.isArray(data.inventory) ? data.inventory : [];
    fillStats();
    renderCasino();
    renderInventory();
    updateCaseButtonsState();

    if (resultEl) {
      resultEl.textContent = data?.case?.description || 'Кейс открыт';
    }
    toast(data?.case?.description || 'Кейс открыт', 'success');
  } catch (err) {
    if (resultEl) resultEl.textContent = err.message || 'Ошибка открытия кейса';
    throw err;
  } finally {
    state.caseOpening = false;
    updateCaseButtonsState();
    if (btn) btn.disabled = false;
  }
}

async function buyUpgrade(upgrade) {
  const button = document.querySelector(`[data-upgrade="${upgrade}"] button`);
  if (button) button.disabled = true;
  $('upgradeResult').textContent = 'Покупаем апгрейд...';
  try {
    const data = await api('/api/casino/upgrade/buy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, upgrade }),
    });
    state.bootstrap.profile = data.profile;
    state.bootstrap.casino = data.casino;
    fillStats();
    renderCasino();
  } finally {
    if (button) button.disabled = false;
  }
}

function handleProofFileSelect(file) {
  if (!file) return;
  state.pendingProofFile = file;

  const dropzoneContent = $('proofDropzoneContent');
  const filePreview = $('proofFilePreview');
  const previewImg = $('proofPreviewImg');
  const fileName = $('proofFileName');
  const fileSize = $('proofFileSize');
  const dropzone = $('proofDropzone');
  const errorHint = $('proofErrorHint');
  const submitBtn = $('submitProofBtn');

  if (errorHint) {
    errorHint.textContent = '';
    errorHint.classList.add('hidden');
  }
  if (dropzone) {
    dropzone.classList.remove('has-error');
    dropzone.classList.add('has-file');
  }

  if (fileName) fileName.textContent = file.name;
  if (fileSize) {
    const sizeKb = (file.size / 1024).toFixed(1);
    const sizeStr = file.size > 1024 * 1024 ? (file.size / (1024 * 1024)).toFixed(2) + ' МБ' : sizeKb + ' КБ';
    fileSize.textContent = `Размер: ${sizeStr}`;
  }

  if (file.type && file.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (previewImg) {
        previewImg.src = e.target.result;
        previewImg.style.display = 'block';
      }
    };
    reader.readAsDataURL(file);
  } else {
    if (previewImg) previewImg.style.display = 'none';
  }

  if (dropzoneContent) dropzoneContent.classList.add('hidden');
  if (filePreview) filePreview.classList.remove('hidden');
  const fileInput = $('proofFile');
  if (fileInput) fileInput.style.pointerEvents = 'none';

  if (submitBtn) {
    submitBtn.textContent = '✅ Отправить чек';
    submitBtn.disabled = false;
  }
}

function clearProofFile() {
  state.pendingProofFile = null;
  const file = $('proofFile');
  if (file) {
    file.value = '';
    file.style.pointerEvents = 'auto';
  }

  const dropzoneContent = $('proofDropzoneContent');
  const filePreview = $('proofFilePreview');
  const previewImg = $('proofPreviewImg');
  const dropzone = $('proofDropzone');
  const errorHint = $('proofErrorHint');
  const submitBtn = $('submitProofBtn');

  if (previewImg) previewImg.src = '';
  if (filePreview) filePreview.classList.add('hidden');
  if (dropzoneContent) dropzoneContent.classList.remove('hidden');
  if (dropzone) dropzone.classList.remove('has-file', 'has-error');
  if (errorHint) {
    errorHint.textContent = '';
    errorHint.classList.add('hidden');
  }
  if (submitBtn) {
    submitBtn.textContent = 'Отправить чек';
    submitBtn.disabled = false;
  }
}

function setProofModal(open) {
  const modal = $('proofModal');
  if (!modal) return;
  modal.classList.toggle('hidden', !open);
  const btn = $('submitProofBtn');
  const cancelBtn = $('cancelProofBtn');
  const closeBtn = $('closeProofModalBtn');
  const file = $('proofFile');
  if (btn) {
    btn.disabled = false;
    btn.textContent = 'Отправить чек';
  }
  if (cancelBtn) cancelBtn.disabled = false;
  if (closeBtn) closeBtn.disabled = false;
  if (file) {
    file.disabled = false;
    if (!open) file.value = '';
  }
  clearProofFile();
  if (!open) {
    state.pendingProof = null;
    state.isUploadingProof = false;
  }
}

function showProofDialog(kind, payload, detailsText) {
  state.pendingProof = { kind, payload };
  const details = $('proofDetails');
  if (details) {
    const msg = detailsText;
    details.textContent = typeof msg === 'string' ? msg : String(msg);
  }
  setProofModal(true);
}

function currentStarsPayload() {
  const targetMode = $('starsTargetMode').value;
  return {
    init_data: state.initData,
    stars: Number($('starsAmount').value || 0),
    payment_method: $('starsPaymentMethod').value,
    target_username: targetMode === 'friend' ? ($('starsTargetUsername').value.trim() || null) : null,
  };
}

function currentPremiumPayload() {
  return {
    init_data: state.initData,
    months: Number($('premiumMonths').value || 1),
    payment_method: $('premiumPaymentMethod').value,
    target_username: $('premiumTargetUsername').value.trim() || null,
  };
}

function currentTonPayload() {
  return {
    init_data: state.initData,
    ton_amount: Number($('tonAmount').value || 0),
    payment_method: $('tonPaymentMethod').value,
  };
}

function summaryFromResponse(type, data) {
  const pd = data.payment_details || {};
  if (type === 'stars' || type === 'premium') {
    if (pd.type === 'mono') return `К оплате: ${fmt(pd.amount_uah)} грн\nКарта Mono: ${pd.mono_card}`;
    if (pd.type === 'ton_wallet') return `К оплате: ${fmt(pd.amount_ton, 4)} TON\nTON адрес: ${pd.ton_address}`;
    return `Списание с TON баланса.\nЦена: ${fmt(data.price_uah)} грн`;
  }
  if (pd.type === 'mono') return `Будет зачислено: ${fmt(data.ton_amount, 4)} TON\nК оплате: ${fmt(pd.amount_uah)} грн\nКарта Mono: ${pd.mono_card}`;
  return `Будет зачислено: ${fmt(data.ton_amount, 4)} TON\nК оплате: ${fmt(pd.amount_ton, 4)} TON\nTON адрес: ${pd.ton_address}`;
}

async function loadBootstrap() {
  if (state.bootstrapLoading) return;
  state.bootstrapLoading = true;
  const refreshBtn = $('refreshBtn');
  if (refreshBtn) refreshBtn.disabled = true;
  try {
  if (!state.initData) {
    enforceTelegramClient();
    return;
  }
  state.bootstrap = await api('/api/bootstrap');
  await loadNftQuotes();
  if (!state.bootstrap.profile) state.bootstrap.profile = { balance_stars: 0, total_stars: 0 };
  if (!Array.isArray(state.bootstrap.inventory)) state.bootstrap.inventory = [];
  if (!state.bootstrap.casino) state.bootstrap.casino = { cases: {}, upgrades: {}, last_case: null, last_upgrade: null };
  fillStats();
  setAdminTabVisibility();
  renderHistory();
  renderReviews();
  renderGameStats();
  renderCasino();
  renderCaseConfigurations();
  renderInventory();
  renderNftShop();
  renderReferrals();
  if (isAdmin()) {
    await loadAdminDashboard();
  }
  updateCrashGraph([]);
  updateCrashActionButtons(false);
  if (state.bootstrap?.mines_session) state.minesSession = state.bootstrap.mines_session;
  renderMinesBoard();
  } catch (err) {
    console.error('loadBootstrap error:', err);
    if (err.message && (err.message.includes('заблокирован') || err.message.includes('403'))) {
      const bannedScreen = $('bannedScreen');
      if (bannedScreen) bannedScreen.classList.remove('hidden');
    } else {
      toast(err.message, 'error');
    }
  } finally {
    state.bootstrapLoading = false;
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

async function previewStars() {
  const data = await api('/api/orders/stars/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentStarsPayload()) });
  const msg = summaryFromResponse('stars', data);
  $('starsPreview').textContent = typeof msg === 'string' ? msg : String(msg);
}

async function createStarsOrder() {
  const data = await api('/api/orders/stars/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentStarsPayload()) });
  if (data.instant) {
    const msg = data.message || 'Готово';
    toast(typeof msg === 'string' ? msg : String(msg));
    state.bootstrap.profile = data.profile;
    state.bootstrap.transactions = data.transactions;
    fillStats();
    renderHistory();
    switchTab('history');
    return;
  }
  const msg2 = summaryFromResponse('stars', data);
  $('starsPreview').textContent = typeof msg2 === 'string' ? msg2 : String(msg2);
  showProofDialog('stars', data, summaryFromResponse('stars', data));
}

async function previewPremium() {
  const data = await api('/api/orders/premium/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentPremiumPayload()) });
  const msg = summaryFromResponse('premium', data);
  $('premiumPreview').textContent = typeof msg === 'string' ? msg : String(msg);
}

async function createPremiumOrder() {
  const data = await api('/api/orders/premium/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentPremiumPayload()) });
  if (data.instant) {
    const msg = data.message || 'Оплачено';
    toast(typeof msg === 'string' ? msg : String(msg));
    state.bootstrap.profile = data.profile;
    state.bootstrap.transactions = data.transactions;
    fillStats();
    renderHistory();
    switchTab('history');
    return;
  }
  const msg2 = summaryFromResponse('premium', data);
  $('premiumPreview').textContent = typeof msg2 === 'string' ? msg2 : String(msg2);
  showProofDialog('premium', { ...data, target_username: $('premiumTargetUsername').value.trim() || null }, summaryFromResponse('premium', data));
}

async function previewTon() {
  const data = await api('/api/orders/ton/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentTonPayload()) });
  const msg = summaryFromResponse('ton', data);
  $('tonPreview').textContent = typeof msg === 'string' ? msg : String(msg);
}

async function createTonOrder() {
  const data = await api('/api/orders/ton/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentTonPayload()) });
  const msg = summaryFromResponse('ton', data);
  $('tonPreview').textContent = typeof msg === 'string' ? msg : String(msg);
  showProofDialog('ton_topup', data, summaryFromResponse('ton', data));
}

async function uploadProof() {
  if (state.isUploadingProof) return;
  if (!state.pendingProof) {
    toast('Сессия заказа устарела. Попробуйте снова.', 'error');
    setProofModal(false);
    return;
  }

  const fileInput = $('proofFile');
  const file = state.pendingProofFile || fileInput?.files?.[0];

  const errorHint = $('proofErrorHint');
  const dropzone = $('proofDropzone');

  if (!file) {
    if (errorHint) {
      errorHint.textContent = '⚠️ Пожалуйста, сначала прикрепите фото или скриншот чека';
      errorHint.classList.remove('hidden');
    }
    if (dropzone) {
      dropzone.classList.remove('has-error');
      void dropzone.offsetWidth;
      dropzone.classList.add('has-error');
    }
    toast('Выберите изображение чека', 'error');
    if (fileInput) fileInput.click();
    return;
  }

  const btn = $('submitProofBtn');
  const cancelBtn = $('cancelProofBtn');
  const closeBtn = $('closeProofModalBtn');

  state.isUploadingProof = true;
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Отправка...';
  }
  if (cancelBtn) cancelBtn.disabled = true;
  if (closeBtn) closeBtn.disabled = true;
  if (fileInput) fileInput.disabled = true;

  try {
    const form = new FormData();
    form.append('init_data', state.initData);
    form.append('kind', state.pendingProof.kind);
    form.append('payload_json', JSON.stringify(state.pendingProof.payload));
    form.append('proof', file);
    const data = await api('/api/proof/upload', { method: 'POST', body: form });
    const msg = data?.message || 'Чек успешно отправлен на проверку администратору!';
    toast(typeof msg === 'string' ? msg : String(msg), 'success');
    state.bootstrap.transactions = data.transactions;
    renderHistory();
    setProofModal(false);
    switchTab('history');
  } catch (err) {
    state.isUploadingProof = false;
    if (btn) {
      btn.disabled = false;
      btn.textContent = '✅ Отправить чек';
    }
    if (cancelBtn) cancelBtn.disabled = false;
    if (closeBtn) closeBtn.disabled = false;
    if (fileInput) fileInput.disabled = false;
    if (errorHint) {
      errorHint.textContent = err.message || 'Ошибка отправки чека';
      errorHint.classList.remove('hidden');
    }
    toast(err.message || 'Ошибка отправки чека', 'error');
  }
}

async function applyPromo() {
  const code = $('promoCode').value.trim();
  const data = await api('/api/promo/apply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: state.initData, code }) });
  toast(`Начислено ${data.credited_stars} ⭐️`);
  state.bootstrap.profile = data.profile;
  fillStats();
}

async function sendSupport(category, text) {
  const data = await api('/api/support/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: state.initData, category, text }) });
  const msg = (data?.message || 'Отправлено');
  toast(typeof msg === 'string' ? msg : String(msg));
}

async function createWithdraw(asset, amount) {
  const data = await api('/api/withdraw/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: state.initData, asset, amount }) });
  const msg = data?.message || 'Заявка отправлена';
  toast(typeof msg === 'string' ? msg : String(msg));
  state.bootstrap.transactions = data.transactions;
  renderHistory();
  switchTab('history');
}

async function sendReview() {
  const text = $('reviewText').value.trim();
  const data = await api('/api/reviews/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ init_data: state.initData, text }) });
  const msg = data?.message || 'Спасибо за отзыв';
  toast(typeof msg === 'string' ? msg : String(msg));
  state.bootstrap.reviews = data.reviews;
  $('reviewText').value = '';
  renderReviews();
}

async function reloadReviews() {
  const data = await api('/api/reviews/recent?limit=5');
  state.bootstrap.reviews = data.reviews;
  renderReviews();
}

function renderReferrals() {
  const ref = state.bootstrap?.referral;
  if (!ref) return;

  const countEl = $('refCount');
  if (countEl) countEl.textContent = ref.referral_count || 0;

  const earnEl = $('refEarnings');
  if (earnEl) earnEl.textContent = fmt(ref.referral_earnings_stars || 0);

  const linkInput = $('refLinkInput');
  if (linkInput) linkInput.value = ref.invite_link || '';

  const listEl = $('referralsList');
  const countHint = $('refListCountHint');
  if (countHint) countHint.textContent = `${ref.referral_count || 0} чел.`;

  if (listEl) {
    const list = Array.isArray(ref.referrals) ? ref.referrals : [];
    if (!list.length) {
      listEl.className = 'stack-list empty-state';
      listEl.innerHTML = 'У вас пока нет приглашённых друзей. Поделитесь ссылкой выше!';
    } else {
      listEl.className = 'stack-list';
      listEl.innerHTML = list.map(item => `
        <div class="cardish ref-item-row">
          <div>
            <strong class="ref-user-name">@${escapeHtml(item.username || 'Пользователь')}</strong>
            <div class="hint ref-user-meta">ID: ${item.user_id} • ${escapeHtml(item.date || '')}</div>
          </div>
          <span class="ref-status-badge">Активен</span>
        </div>
      `).join('');
    }
  }
}

function copyReferralLink() {
  const linkInput = $('refLinkInput');
  const text = linkInput ? linkInput.value : '';
  if (!text || text === 'Загрузка ссылки...') {
    toast('Ссылка ещё загружается', 'info');
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showRefCopySuccess();
    }).catch(() => {
      fallbackCopyText(text);
    });
  } else {
    fallbackCopyText(text);
  }
}

function fallbackCopyText(text) {
  const linkInput = $('refLinkInput');
  if (linkInput) {
    linkInput.select();
    linkInput.setSelectionRange(0, 99999);
    try {
      document.execCommand('copy');
      showRefCopySuccess();
      return;
    } catch (_) {}
  }
  toast('Скопируйте ссылку: ' + text, 'info');
}

function showRefCopySuccess() {
  const toastEl = $('refCopyToast');
  if (toastEl) {
    toastEl.style.display = 'block';
    setTimeout(() => { toastEl.style.display = 'none'; }, 2500);
  }
  if (window.Telegram?.WebApp?.showPopup) {
    Telegram.WebApp.showPopup({
      title: 'Скопировано!',
      message: 'Реферальная ссылка скопирована в буфер обмена.',
      buttons: [{ type: 'ok' }]
    });
  } else {
    toast('Реферальная ссылка скопирована!', 'success');
  }
}

function shareReferralLink() {
  const ref = state.bootstrap?.referral;
  const link = ref?.invite_link || $('refLinkInput')?.value || '';
  if (!link) {
    toast('Ссылка недоступна', 'error');
    return;
  }
  const shareText = '⭐️ Заходи в Freaking Stars! Покупай Stars и Telegram Premium выгодно, крути кейсы и выигрывай!';
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;
  if (window.Telegram?.WebApp?.openTelegramLink) {
    window.Telegram.WebApp.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, '_blank');
  }
}

async function adminSaveStarPackages() {
  const raw = $('adminStarPackagesJson').value.trim();
  const packages = JSON.parse(raw);
  await api('/api/admin/prices/star-packages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, packages }),
  });
  toast('Stars пакеты сохранены');
  await loadAdminDashboard();
}

async function adminSavePremiumPrices() {
  const raw = $('adminPremiumJson').value.trim();
  const prices = JSON.parse(raw);
  await api('/api/admin/prices/premium', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, prices }),
  });
  toast('Premium цены сохранены');
  await loadAdminDashboard();
}

async function adminSaveNftPrices() {
  const prices = {};
  document.querySelectorAll('[data-nft-model]').forEach((input) => {
    const model = String(input.dataset.nftModel || '').trim().toLowerCase();
    const value = Number(input.value || 0);
    if (model && Number.isFinite(value) && value > 0) {
      prices[model] = Math.round(value);
    }
  });
  await api('/api/admin/prices/nft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, prices }),
  });
  toast('NFT цены сохранены');
  await loadAdminDashboard();
}

async function adminSaveNftImages() {
  const images = {};
  document.querySelectorAll('[data-nft-image-model]').forEach((input) => {
    const model = String(input.dataset.nftImageModel || '').trim().toLowerCase();
    const value = String(input.value || '').trim();
    if (model) images[model] = value;
  });
  await api('/api/admin/prices/nft-images', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, images }),
  });
  toast('Ссылки NFT изображений сохранены');
  await loadAdminDashboard();
}

async function adminSaveNftCaseChances() {
  const groupedByTier = {};
  const legacyChances = {};

  document.querySelectorAll('input[data-case-tier][data-case-item-id]').forEach((input) => {
    const tier = String(input.dataset.caseTier || '').trim();
    const itemId = String(input.dataset.caseItemId || '').trim();
    const val = Number(input.value || 0);
    if (tier && itemId && Number.isFinite(val) && val >= 0) {
      if (!groupedByTier[tier]) groupedByTier[tier] = {};
      const rounded = Math.round(val * 100) / 100;
      groupedByTier[tier][itemId] = rounded;
      const model = input.dataset.nftCaseChanceModel;
      if (model) legacyChances[model] = rounded;
    }
  });

  try {
    await api('/api/admin/prices/case-chances', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, chances: groupedByTier }),
    });
  } catch (err) {
    console.error('Failed to save case chances via case-chances API:', err);
  }

  try {
    if (Object.keys(legacyChances).length) {
      await api('/api/admin/prices/nft-case-chances', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: state.initData, chances: legacyChances }),
      });
    }
  } catch (err) {
    // optional fallback
  }

  toast('Шансы призов для всех кейсов успешно сохранены');
  await loadAdminDashboard();
}

async function adminSaveGameRtp() {
  const rtp_percent = {
    mines: Number($('adminRtpMines').value || 0),
    crash: Number($('adminRtpCrash').value || 0),
    roulette: Number($('adminRtpRoulette').value || 0),
    cases: Number($('adminRtpCases').value || 0),
    case150: Number($('adminRtpCase150').value || 0),
    case250: Number($('adminRtpCase250').value || 0),
    case400: Number($('adminRtpCase400').value || 0),
    case600: Number($('adminRtpCase600').value || 0),
    upgrade: Number($('adminRtpUpgrade')?.value || 95),
  };
  await api('/api/admin/games/rtp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, rtp_percent }),
  });
  toast('RTP по играм сохранён');
  await loadAdminDashboard();
}

async function adminSaveCoinSettings() {
  const minBet = Number($('adminCoinMinBet').value || 0);
  const maxBet = Number($('adminCoinMaxBet').value || 0);
  const odds = {
    eagle: Number($('adminCoinOddsEagle').value || 0),
    tails: Number($('adminCoinOddsTails').value || 0),
    edge: Number($('adminCoinOddsEdge').value || 0),
  };
  const multipliers = {
    eagle: Number($('adminCoinMulEagle').value || 0),
    tails: Number($('adminCoinMulTails').value || 0),
    edge: Number($('adminCoinMulEdge').value || 0),
  };
  if (minBet <= 0 || maxBet <= 0 || minBet > maxBet) {
    toast('Проверьте минимальную и максимальную ставки', 'error');
    return;
  }
  if (odds.eagle < 0 || odds.tails < 0 || odds.edge < 0) {
    toast('Шансы не могут быть отрицательными', 'error');
    return;
  }
  await api('/api/admin/games/coin-settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      init_data: state.initData,
      min_bet: minBet,
      max_bet: maxBet,
      odds,
      multipliers,
    }),
  });
  toast('Настройки монетки сохранены');
  await loadAdminDashboard();
}

async function adminCreatePromocode() {
  const code = $('adminPromoCode').value.trim();
  const maxUses = Number($('adminPromoMaxUses').value || 0);
  const amountStars = Number($('adminPromoAmount').value || 0);
  await api('/api/admin/promocodes/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      init_data: state.initData,
      code,
      max_uses: maxUses,
      amount_stars: amountStars,
    }),
  });
  toast('Промокод создан');
  $('adminPromoCode').value = '';
  await loadAdminDashboard();
}

async function adminTrackUser() {
  const identifier = $('adminTrackInput').value.trim();
  if (!identifier) {
    toast('Введите ID или @username', 'error');
    return;
  }
  const data = await api(`/api/admin/track-user?identifier=${encodeURIComponent(identifier)}`);
  const trackedId = Number(data?.user?.id || 0);
  state.adminTrackedUserId = Number.isFinite(trackedId) && trackedId > 0 ? trackedId : null;
  if ($('adminResetMinesBtn')) $('adminResetMinesBtn').disabled = !state.adminTrackedUserId;
  if ($('adminResetAllGamesBtn')) $('adminResetAllGamesBtn').disabled = !state.adminTrackedUserId;
  $('adminTrackResult').textContent = JSON.stringify(data, null, 2);
}

async function adminResetTrackedUserMines() {
  if (!state.adminTrackedUserId) {
    toast('Сначала найдите пользователя', 'error');
    return;
  }
  const data = await api('/api/admin/users/reset-mines-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      init_data: state.initData,
      user_id: state.adminTrackedUserId,
    }),
  });
  toast(data?.had_active_session ? 'Сессия мин сброшена' : 'Активной сессии мин не было');
  await adminTrackUser();
}

async function adminResetTrackedUserAllGames() {
  if (!state.adminTrackedUserId) {
    toast('Сначала найдите пользователя', 'error');
    return;
  }
  const data = await api('/api/admin/users/reset-all-games', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      init_data: state.initData,
      user_id: state.adminTrackedUserId,
    }),
  });
  if (data?.had_active_session) {
    const list = Array.isArray(data.reset_games) ? data.reset_games.join(', ') : 'игры';
    toast(`Активные игры сброшены: ${list}`, 'success');
  } else {
    toast('У пользователя не было активных игр', 'info');
  }
  await adminTrackUser();
}

async function adminSendBroadcast() {
  const text = $('adminBroadcastText').value.trim();
  await api('/api/admin/broadcast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, text }),
  });
  toast('Рассылка выполнена');
  $('adminBroadcastText').value = '';
}

async function adminClearGameStats() {
  await api('/api/admin/clear-game-stats', { method: 'POST' });
  toast('Статистика игр очищена');
  await loadAdminDashboard();
}

async function adminRejectAllPending() {
  if (!confirm('Вы действительно хотите отклонить ВСЕ висящие заявки?')) return;
  try {
    const res = await api('/api/admin/transactions/reject-all-pending', { method: 'POST' });
    toast(`Отклонено висящих заявок: ${res.rejected_count || 0}`);
    await loadAdminDashboard();
  } catch (err) {
    toast(err.message, 'error');
  }
}

function openGame(name) {
  state.activeGame = name;
  const screen = $('gameScreen');
  screen.classList.remove('hidden');
  requestAnimationFrame(() => screen.classList.add('open'));
  document.querySelectorAll('.game-view').forEach(view => {
    view.classList.remove('active');
    view.classList.add('hidden');
  });
  const titleMap = { roulette: 'Рулетка', mines: 'Мины', crash: 'Crash', coin: 'Монетка', plinko: 'Plinko', tower: 'Tower', blackjack: 'Blackjack', upgrade: 'Апгрейды' };
  $('gameScreenTitle').textContent = titleMap[name] || 'Игра';
  const target = $(`game${name[0].toUpperCase()}${name.slice(1)}`);
  if (target) {
    target.classList.remove('hidden');
    target.classList.add('active');
  }
  if (name === 'plinko') {
    setTimeout(drawPlinkoBoard, 50);
    updatePlinkoBallHint();
  }
  if (name === 'tower') initTowerUI();
  if (name === 'blackjack') initBlackjackUI();
  if (name === 'upgrade') initUpgradeUI();
}

function closeGame() {
  state.activeGame = null;
  const screen = $('gameScreen');
  screen.classList.remove('open');
  screen.classList.add('hidden');
  document.querySelectorAll('.game-view').forEach(view => {
    view.classList.remove('active');
    view.classList.add('hidden');
  });
}

function rouletteTargetRotation(color) {
  const sector = 360 / 31;
  const indices = color === 'green' ? [0] : Array.from({ length: 30 }, (_, i) => i + 1).filter(i => color === 'red' ? i % 2 === 1 : i % 2 === 0);
  const index = indices[Math.floor(Math.random() * indices.length)];
  const centerAngle = (index + 0.5) * sector;
  // The pointer is at the top, and CSS conic-gradient starts at the top too.
  // Rotate the wheel so the selected sector center moves to 0°.
  return 360 * 6 - centerAngle;
}

async function playRoulette() {
  const button = $('roulettePlayBtn');
  button.classList.add('hidden');
  $('rouletteResult').textContent = 'Барабан раскручивается…';
  try {
    const data = await api('/api/games/roulette/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        amount: Number($('rouletteAmount').value || 0),
        currency: $('rouletteCurrency').value,
        color: $('rouletteColor').value,
      })
    });
    state.bootstrap.profile = data.profile;
    state.bootstrap.games = data.games;
    fillStats();
    renderGameStats();
    const wheel = $('rouletteWheel');
    state.rouletteRotation += rouletteTargetRotation(data.result_color);
    wheel.style.transform = `rotate(${state.rouletteRotation}deg)`;
    await sleep(5200);
    $('rouletteResult').textContent = data.win
      ? `Выпало: ${translateColor(data.result_color)}. Победа, выплата ${fmt(data.payout, 4)}.`
      : `Выпало: ${translateColor(data.result_color)}. Ставка проиграла.`;
  } finally {
    button.classList.remove('hidden');
  }
}

async function playCoin() {
  const button = $('coinPlayBtn');
  const coinAnimation = $('coinAnimation');
  const coinLabel = $('coinAnimationLabel');
  button.classList.add('hidden');

  $('coinResult').textContent = 'Монета в воздухе...';
  if (coinAnimation) {
    coinAnimation.classList.remove('coin-face-eagle', 'coin-face-tails', 'coin-face-edge');
    coinAnimation.classList.remove('coin-flip');
    void coinAnimation.offsetWidth;
    coinAnimation.classList.add('coin-flip');
  }
  if (coinLabel) coinLabel.textContent = 'Бросок...';

  try {
    const data = await api('/api/games/coin/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        amount: Number($('coinAmount').value || 0),
        currency: $('coinCurrency').value,
        choice: $('coinChoice').value,
      })
    });

    await sleep(1200);
    if (coinAnimation) {
      coinAnimation.classList.remove('coin-flip');
      void coinAnimation.offsetWidth;
      coinAnimation.classList.add(`coin-face-${data.result}`);
    }
    if (coinLabel) coinLabel.textContent = translateCoinResult(data.result);

    state.bootstrap.profile = data.profile;
    state.bootstrap.games = data.games;
    fillStats();
    renderGameStats();

    $('coinResult').textContent = data.win
      ? `Выпало: ${translateCoinResult(data.result)}. Победа, выплата ${fmt(data.payout, 4)}.`
      : `Выпало: ${translateCoinResult(data.result)}. Ставка проиграла.`;
  } catch (err) {
    $('coinResult').textContent = err.message || 'Ошибка запроса';
    throw err;
  } finally {
    button.classList.remove('hidden');
  }
}

function translateCoinResult(result) {
  if (result === 'eagle') return 'Орёл';
  if (result === 'tails') return 'Решка';
  if (result === 'edge') return 'Ребро';
  return result;
}

function translateColor(color) {
  return color === 'red' ? 'красное' : color === 'white' ? 'белое' : 'зелёное';
}

function renderMinesBoard() {
  const wrap = $('minesBoard');
  if (!wrap) return;
  const revealed = new Set(state.minesSession?.revealed || []);
  const mines = new Set(state.minesSession?.mines || []);
  wrap.innerHTML = Array.from({ length: 16 }, (_, idx) => {
    let cls = 'mine-cell';
    let text = '•';
    if (revealed.has(idx)) { cls += ' safe'; text = '💎'; }
    if (mines.has(idx)) { cls += ' mine'; text = '💣'; }
    return `<button class="${cls}" data-mine-index="${idx}">${text}</button>`;
  }).join('');
  wrap.querySelectorAll('[data-mine-index]').forEach(btn => btn.addEventListener('click', () => revealMine(Number(btn.dataset.mineIndex))));

  const isGameActive = Boolean(state.minesSession && !state.minesSession.mines);
  $('minesStartBtn')?.classList.toggle('hidden', isGameActive);
  $('minesCashoutBtn')?.classList.toggle('hidden', !isGameActive);
}

async function startMines() {
  try {
    const data = await api('/api/games/mines/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, amount: Number($('minesAmount').value || 0), currency: $('minesCurrency').value })
    });
    state.bootstrap.profile = data.profile;
    state.minesSession = data.session;
    fillStats();
    renderMinesBoard();
    $('minesStatus').textContent = 'Игра началась. Открывайте безопасные клетки.';
  } catch (err) {
    const msg = String(err?.message || '');
    if (msg.includes('активная игра')) {
      await loadBootstrap();
      if (state.minesSession) {
        renderMinesBoard();
        $('minesStatus').textContent = 'Восстановлена активная игра. Продолжайте открывать клетки.';
        toast('У вас уже была активная игра в мины. Сессия восстановлена.');
        return;
      }
    }
    throw err;
  }
}

async function revealMine(index) {
  if (!state.minesSession) return toast('Сначала начните игру', 'error');
  const data = await api('/api/games/mines/reveal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData, index })
  });
  if (data.hit_mine) {
    state.bootstrap.profile = data.profile;
    state.bootstrap.games = data.games;
    state.minesSession = { revealed: [], mines: data.mines };
    fillStats();
    renderGameStats();
    renderMinesBoard();
    $('minesStatus').textContent = 'Вы наткнулись на мину.';
    await sleep(1500);
    state.minesSession = null;
    renderMinesBoard();
    return;
  }
  state.minesSession = { ...state.minesSession, revealed: data.revealed, safe_clicks: data.safe_clicks };
  renderMinesBoard();
  $('minesStatus').textContent = `Безопасных клеток: ${data.safe_clicks}. Текущий x${fmt(data.current_multiplier, 2)}.`;
}

async function cashoutMines() {
  if (!state.minesSession) return toast('Нет активной игры', 'error');
  const form = new FormData();
  form.append('init_data', state.initData);
  const data = await api('/api/games/mines/cashout', { method: 'POST', body: form });
  state.bootstrap.profile = data.profile;
  state.bootstrap.games = data.games;
  fillStats();
  renderGameStats();
  $('minesStatus').textContent = `Забрано ${fmt(data.payout, 4)} по x${fmt(data.multiplier, 2)}.`;
  state.minesSession = null;
  renderMinesBoard();
}

function setCrashButtons(active) {
  const playBtn = $('crashPlayBtn');
  const cashoutBtn = $('crashCashoutBtn');
  if (playBtn) {
    playBtn.disabled = active;
    playBtn.classList.toggle('hidden', active);
  }
  if (cashoutBtn) {
    cashoutBtn.disabled = !active;
    cashoutBtn.classList.toggle('hidden', !active);
  }
}

async function finishCrashSession() {
  const data = await api('/api/games/crash/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: state.initData })
  });
  state.bootstrap.profile = data.profile;
  state.bootstrap.games = data.games;
  fillStats();
  renderGameStats();
  setCrashButtons(false);
  updateCrashActionButtons(false);
  state.crashSession = null;
  state.crashActive = false;
  $('crashResult').textContent = `Раунд упал на ${fmt(data.crash_point, 2)}x. Вы не успели забрать.`;
}

async function cashoutCrash() {
  if (!state.crashActive || !state.crashSession) return;
  const cashoutX = Math.max(1, Number(state.crashCurrentX.toFixed(2)));
  setCrashButtons(false);
  $('crashResult').textContent = `Забираем x${fmt(cashoutX, 2)}...`;
  try {
    const data = await api('/api/games/crash/cashout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, cashout_x: cashoutX })
    });
    state.bootstrap.profile = data.profile;
    state.bootstrap.games = data.games;
    fillStats();
    renderGameStats();
    const resultText = data.won
      ? `Вы успели! Выплата ${fmt(data.payout, 4)} по x${fmt(data.cashout_x, 2)}.`
      : `Вы не успели: раунд упал на ${fmt(data.crash_point, 2)}x.`;
    $('crashResult').textContent = resultText;
  } catch (err) {
    $('crashResult').textContent = err.message;
  } finally {
    state.crashSession = null;
    state.crashActive = false;
    updateCrashActionButtons(false);
  }
}

async function animateCrash() {
  const live = $('crashLiveValue');
  const stage = document.querySelector('.crash-stage');
  const stream = $('crashMultiplierStream');
  if (stage) stage.classList.add('is-running');
  if (stream) stream.replaceChildren();
  updateCrashGraph([]);
  state.crashCurrentX = 1.0;
  let nextCoefficient = 1.1;
  const history = [1.0];
  while (state.crashActive) {
    let step = 0.01;
    if (state.crashCurrentX >= 3.50) {
      step = 0.04;
    } else if (state.crashCurrentX >= 1.45) {
      step = 0.02;
    }
    state.crashCurrentX = Number((state.crashCurrentX + step).toFixed(2));
    history.push(state.crashCurrentX);
    if (live) live.textContent = `${fmt(state.crashCurrentX, 2)}x`;
    updateCrashGraph(history);
    if (state.crashCurrentX >= nextCoefficient) {
      spawnCrashCoefficient(state.crashCurrentX);
      nextCoefficient = state.crashCurrentX + Math.max(0.18, state.crashCurrentX * 0.13);
    }
    if (state.crashCurrentX >= 100.0) {
      break;
    }
    const delay = 100 + Math.random() * 20;
    await sleep(delay);
  }
  stage?.classList.remove('is-running');
}

async function playCrash() {
  if (state.crashActive) return;
  const button = $('crashPlayBtn');
  setCrashButtons(false);
  updateCrashActionButtons(true);
  $('crashResult').textContent = 'Раунд начинается…';
  state.crashActive = true;
  const amount = Number($('crashAmount').value || 0);
  const currency = $('crashCurrency').value;
  try {
    const data = await api('/api/games/crash/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, amount, currency, auto_cashout: null })
    });
    state.bootstrap.profile = data.profile;
    state.bootstrap.games = data.games;
    fillStats();
    renderGameStats();
    state.crashSession = { amount, currency, started_at_ts: data.started_at_ts };
    setCrashButtons(true);
    updateCrashActionButtons(true);
    state.crashCurrentX = 1.0;
    await animateCrash();
    if (state.crashActive) {
      state.crashActive = false;
      setCrashButtons(false);
      await finishCrashSession();
    }
  } catch (err) {
    state.crashActive = false;
    document.querySelector('.crash-stage')?.classList.remove('is-running');
    $('crashResult').textContent = err.message;
  } finally {
    button.disabled = false;
    if (!state.crashActive) updateCrashActionButtons(false);
    setCrashButtons(false);
  }
}

/* ==============================================================================
   PLINKO LOGIC & CANVAS ENGINE
   ============================================================================== */
let plinkoActive = false;

const CLIENT_PLINKO_MULTIPLIERS = {
  8: {
    low: [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
    medium: [13, 3, 1.3, 0.7, 0.4, 0.7, 1.3, 3, 13],
    high: [29, 4, 1.5, 0.3, 0.2, 0.3, 1.5, 4, 29],
  },
  10: {
    low: [8.9, 3, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 3, 8.9],
    medium: [22, 5, 2, 1.4, 0.6, 0.4, 0.6, 1.4, 2, 5, 22],
    high: [76, 10, 3, 1.4, 0.3, 0.2, 0.3, 1.4, 3, 10, 76],
  },
  12: {
    low: [10, 3, 1.6, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 1.6, 3, 10],
    medium: [33, 11, 4, 2, 1.1, 0.6, 0.3, 0.6, 1.1, 2, 4, 11, 33],
    high: [170, 24, 8.1, 2, 0.7, 0.2, 0.2, 0.2, 0.7, 2, 8.1, 24, 170],
  },
  14: {
    low: [7.1, 4, 1.9, 1.4, 1.3, 1.1, 1, 0.5, 1, 1.1, 1.3, 1.4, 1.9, 4, 7.1],
    medium: [58, 15, 7, 4, 1.9, 1, 0.5, 0.2, 0.5, 1, 1.9, 4, 7, 15, 58],
    high: [420, 110, 18, 5, 1.9, 0.3, 0.2, 0.2, 0.2, 0.3, 1.9, 5, 18, 110, 420],
  },
  16: {
    low: [16, 9, 2, 1.4, 1.4, 1.2, 1.1, 1, 0.5, 1, 1.1, 1.2, 1.4, 1.4, 2, 9, 16],
    medium: [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 10, 41, 110],
    high: [1000, 130, 26, 9, 4, 2, 0.2, 0.2, 0.2, 0.2, 0.2, 2, 4, 9, 26, 130, 1000],
  }
};

function getPlinkoMultipliers(rows, risk) {
  return CLIENT_PLINKO_MULTIPLIERS[rows]?.[risk] || CLIENT_PLINKO_MULTIPLIERS[10]['medium'];
}

function drawPlinkoBoard(highlightSlot = -1, bounceOffset = 0, multiBounces = null) {
  const canvas = $('plinkoCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const rows = parseInt($('plinkoRows')?.value || 10);
  const risk = $('plinkoRisk')?.value || 'medium';
  const multipliers = getPlinkoMultipliers(rows, risk);

  ctx.clearRect(0, 0, w, h);

  const topY = Math.round(h * 0.052);
  const basketHeight = Math.round(Math.max(40, h * 0.076));
  const basketY = h - basketHeight - 14;
  const pinAreaHeight = basketY - topY - 18;
  const pinSpacingY = pinAreaHeight / (rows + 1);
  const pinSpacingX = (w - 32) / (rows + 2);

  // Draw triangular pegs
  const pinRadius = Math.max(3.8, Math.min(5.5, pinSpacingX * 0.11));
  ctx.save();
  for (let r = 0; r <= rows; r++) {
    const pinsInRow = r + 3;
    const rowWidth = (pinsInRow - 1) * pinSpacingX;
    const startX = (w - rowWidth) / 2;
    const y = topY + r * pinSpacingY;
    for (let i = 0; i < pinsInRow; i++) {
      const px = startX + i * pinSpacingX;
      ctx.beginPath();
      ctx.arc(px, y, pinRadius, 0, Math.PI * 2);
      ctx.fillStyle = '#f1f5f9';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.45)';
      ctx.shadowBlur = 4;
      ctx.fill();
    }
  }
  ctx.restore();

  // Draw Baskets (Корзинки) at the bottom
  const lastRowPins = rows + 3;
  const lastRowWidth = (lastRowPins - 1) * pinSpacingX;
  const lastStartX = (w - lastRowWidth) / 2;
  const totalSlots = multipliers.length;

  for (let i = 0; i < totalSlots; i++) {
    const m = multipliers[i];
    const slotX = lastStartX + (i + 1) * pinSpacingX;
    const slotW = pinSpacingX - 2.5;
    let isLit = (i === highlightSlot);
    let curBounce = (isLit ? bounceOffset : 0);
    if (multiBounces && typeof multiBounces[i] === 'number') {
      isLit = true;
      curBounce = Math.max(curBounce, multiBounces[i]);
    }
    const curBasketY = basketY - curBounce;

    // Basket background color based on multiplier value
    let bgColor = '#4f46e5';
    let glowColor = 'rgba(79, 70, 229, 0.7)';
    if (m >= 100) {
      bgColor = '#ff0055';
      glowColor = 'rgba(255, 0, 85, 0.85)';
    } else if (m >= 10) {
      bgColor = '#ef4444';
      glowColor = 'rgba(239, 68, 68, 0.75)';
    } else if (m >= 3) {
      bgColor = '#f97316';
      glowColor = 'rgba(249, 115, 22, 0.75)';
    } else if (m >= 1.5) {
      bgColor = '#eab308';
      glowColor = 'rgba(234, 179, 8, 0.75)';
    } else if (m >= 1) {
      bgColor = '#10b981';
      glowColor = 'rgba(16, 185, 129, 0.75)';
    } else {
      bgColor = '#4338ca';
      glowColor = 'rgba(99, 102, 241, 0.6)';
    }

    ctx.save();
    ctx.fillStyle = bgColor;
    if (isLit) {
      ctx.shadowColor = glowColor;
      ctx.shadowBlur = 20;
    }

    // Bucket body
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(slotX - slotW / 2, curBasketY, slotW, basketHeight, [6, 6, 8, 8]);
    } else {
      ctx.rect(slotX - slotW / 2, curBasketY, slotW, basketHeight);
    }
    ctx.fill();

    // Bucket top rim
    ctx.fillStyle = isLit ? '#ffffff' : 'rgba(255,255,255,0.5)';
    ctx.fillRect(slotX - slotW / 2, curBasketY, slotW, 3.5);

    // Multiplier text inside basket
    const fontSize = Math.max(9.5, Math.min(13.5, Math.floor(slotW * 0.38)));
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold ' + fontSize + 'px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    let label = `${m}x`;
    if (m >= 1000 && slotW < 32) label = '1kx';
    ctx.fillText(label, slotX, curBasketY + basketHeight / 2 + 1);

    // Vertical separator walls
    ctx.fillStyle = 'rgba(255,255,255,0.45)';
    ctx.fillRect(slotX - slotW / 2 - 1, curBasketY - 5, 2, basketHeight + 5);
    if (i === totalSlots - 1) {
      ctx.fillRect(slotX + slotW / 2 - 1, curBasketY - 5, 2, basketHeight + 5);
    }
    ctx.restore();
  }
}

function updatePlinkoBallHint() {
  const amount = Number($('plinkoAmount')?.value || 10);
  const balls = Math.max(1, parseInt($('plinkoBalls')?.value || 1));
  const currency = $('plinkoCurrency')?.value || 'stars';
  const currSymbol = currency === 'ton' ? 'TON' : '⭐';
  const betPerBall = amount / balls;
  const formattedPrice = currency === 'ton' ? betPerBall.toFixed(4) : (Number.isInteger(betPerBall) ? betPerBall : betPerBall.toFixed(2));
  
  const hintVal = $('plinkoPerBallVal');
  if (hintVal) {
    hintVal.textContent = `${formattedPrice} ${currSymbol}`;
  }
  const btn = $('plinkoPlayBtn');
  if (btn && !plinkoActive) {
    btn.textContent = balls > 1 ? `Бросить ${balls} шариков` : 'Бросить шарик';
  }
}

function setPlinkoControlsDisabled(disabled) {
  ['plinkoAmount', 'plinkoCurrency', 'plinkoBalls', 'plinkoRows', 'plinkoRisk', 'plinkoPlayBtn'].forEach(id => {
    const el = $(id);
    if (el) el.disabled = disabled;
  });
}

async function playPlinko() {
  if (plinkoActive) return;
  const btn = $('plinkoPlayBtn');
  btn.classList.add('hidden');
  plinkoActive = true;
  setPlinkoControlsDisabled(true);

  const ballsCount = Math.max(1, parseInt($('plinkoBalls')?.value || 1));
  const currency = $('plinkoCurrency')?.value || 'stars';
  const currSymbol = currency === 'ton' ? 'TON' : '⭐';
  const totalBet = Number($('plinkoAmount')?.value || 0);

  $('plinkoResult').textContent = ballsCount > 1 ? `Бросаем ${ballsCount} шариков...` : 'Шарик в игре...';

  const rows = parseInt($('plinkoRows').value);
  const risk = $('plinkoRisk').value;

  try {
    const data = await api('/api/games/plinko/drop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        amount: totalBet,
        currency,
        rows,
        risk,
        balls: ballsCount
      })
    });

    const drops = Array.isArray(data.drops) && data.drops.length > 0
      ? data.drops
      : [{ path: data.path, slot_index: data.slot_index, multiplier: data.multiplier, payout: data.payout }];

    await animatePlinkoDrops(rows, drops, data.multipliers || getPlinkoMultipliers(rows, risk));

    state.bootstrap.profile = data.profile;
    if (data.games) state.bootstrap.games = data.games;
    fillStats();
    if (typeof renderGameStats === 'function') renderGameStats();

    const payoutStr = fmt(data.payout, currency === 'ton' ? 4 : 2);
    if (drops.length > 1) {
      const diff = Number((data.payout - totalBet).toFixed(currency === 'ton' ? 4 : 2));
      const diffStr = diff >= 0 ? `+${diff}` : `${diff}`;
      const winCol = diff >= 0 ? '#4ade80' : '#f87171';
      $('plinkoResult').innerHTML = `Выпало шариков: <strong>${drops.length}</strong> • Выплата: <span style="color: ${winCol}; font-weight: 800;">${payoutStr} ${currSymbol}</span> (${diffStr} ${currSymbol})`;
    } else {
      const isWin = data.multiplier >= 1;
      const col = isWin ? '#4ade80' : '#f87171';
      $('plinkoResult').innerHTML = `Выпало: <strong style="color: #ffd55b;">x${data.multiplier}</strong> • Выплата: <span style="color: ${col}; font-weight: 800;">${payoutStr} ${currSymbol}</span>`;
    }
  } catch(err) {
    $('plinkoResult').textContent = err.message;
  } finally {
    plinkoActive = false;
    setPlinkoControlsDisabled(false);
    btn.classList.remove('hidden');
    updatePlinkoBallHint();
  }
}

function animatePlinkoDrops(rows, drops, multipliers) {
  return new Promise(resolve => {
    const canvas = $('plinkoCanvas');
    if (!canvas) { resolve(); return; }
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    const topY = Math.round(h * 0.052);
    const basketHeight = Math.round(Math.max(40, h * 0.076));
    const basketY = h - basketHeight - 14;
    const pinAreaHeight = basketY - topY - 18;
    const pinSpacingY = pinAreaHeight / (rows + 1);
    const pinSpacingX = (w - 32) / (rows + 2);
    const ballRadius = Math.max(5.5, Math.min(9.5, pinSpacingX * 0.28));

    const row0Width = 2 * pinSpacingX;
    const row0StartX = (w - row0Width) / 2;

    const delayBetween = drops.length > 15 ? 4 : (drops.length > 5 ? 6 : 8);
    const balls = drops.map((drop, idx) => ({
      path: drop.path,
      slotIndex: drop.slot_index,
      delay: idx * delayBetween,
      started: false,
      currentStep: 0,
      frame: 0,
      stepFrames: 10,
      currentPinX: row0StartX + 1 * pinSpacingX,
      currentPinY: topY,
      currentPinIdx: 1,
      ballX: row0StartX + 1 * pinSpacingX,
      ballY: topY - 18,
      bounceFrame: 0,
      finished: false,
    }));

    let globalFrame = 0;
    const multiBounces = {};

    function anim() {
      globalFrame++;
      let allDone = true;

      // Decay basket bounces
      for (const slot in multiBounces) {
        if (multiBounces[slot] > 0) {
          multiBounces[slot] -= 0.6;
          if (multiBounces[slot] <= 0) delete multiBounces[slot];
        }
      }

      for (let i = 0; i < balls.length; i++) {
        const b = balls[i];
        if (globalFrame < b.delay) {
          allDone = false;
          continue;
        }
        b.started = true;

        if (b.currentStep < b.path.length) {
          allDone = false;
          const progress = b.frame / b.stepFrames;
          const dir = b.path[b.currentStep];

          const nextPinsInRow = (b.currentStep + 1) + 3;
          const nextRowWidth = (nextPinsInRow - 1) * pinSpacingX;
          const nextStartX = (w - nextRowWidth) / 2;
          const targetPinIdx = b.currentPinIdx + dir;
          const targetX = nextStartX + targetPinIdx * pinSpacingX;
          const targetY = topY + (b.currentStep + 1) * pinSpacingY;

          b.ballX = b.currentPinX + (targetX - b.currentPinX) * progress;
          const arcY = Math.sin(progress * Math.PI) * -14;
          b.ballY = b.currentPinY + (targetY - b.currentPinY) * progress + arcY;

          b.frame++;
          if (b.frame > b.stepFrames) {
            b.frame = 0;
            b.currentStep++;
            b.currentPinX = targetX;
            b.currentPinY = targetY;
            b.currentPinIdx = targetPinIdx;
          }
        } else if (b.bounceFrame <= 18) {
          allDone = false;
          const lastRowPins = rows + 3;
          const lastRowWidth = (lastRowPins - 1) * pinSpacingX;
          const lastStartX = (w - lastRowWidth) / 2;
          const targetBasketX = lastStartX + (b.slotIndex + 1) * pinSpacingX;
          const targetBasketY = basketY + basketHeight / 2;

          const dropProgress = Math.min(1, b.bounceFrame / 8);
          b.ballX = targetBasketX;
          b.ballY = b.currentPinY + (targetBasketY - b.currentPinY) * dropProgress;

          const bounce = Math.sin(b.bounceFrame * 0.32) * 8;
          multiBounces[b.slotIndex] = Math.max(multiBounces[b.slotIndex] || 0, bounce);
          b.bounceFrame++;
        } else {
          b.finished = true;
        }
      }

      drawPlinkoBoard(-1, 0, multiBounces);

      // Render balls
      for (let i = 0; i < balls.length; i++) {
        const b = balls[i];
        if (b.started && !b.finished) {
          ctx.save();
          ctx.fillStyle = '#ffcf4d';
          ctx.shadowColor = '#ffcf4d';
          ctx.shadowBlur = 12;
          ctx.beginPath();
          ctx.arc(b.ballX, b.ballY, ballRadius, 0, Math.PI * 2);
          ctx.fill();

          ctx.fillStyle = '#ffffff';
          ctx.beginPath();
          ctx.arc(b.ballX - ballRadius * 0.28, b.ballY - ballRadius * 0.28, ballRadius * 0.35, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }

      if (allDone) {
        drawPlinkoBoard();
        resolve();
      } else {
        requestAnimationFrame(anim);
      }
    }

    requestAnimationFrame(anim);
  });
}

function animatePlinkoDrop(rows, path, slotIndex, multipliers) {
  return animatePlinkoDrops(rows, [{ path, slot_index: slotIndex }], multipliers);
}

/* ==============================================================================
   TOWER LOGIC (Ступеньки / Башня)
   ============================================================================== */
let towerActive = false;
let towerAwaitingCashout = false;
let towerFloor = 0;
let towerDifficulty = 'medium';
let towerMultipliers = [];

const CLIENT_TOWER_CONFIGS = {
  easy: { tiles: 4, multipliers: [1.25, 1.62, 2.10, 2.75, 3.60, 4.80, 6.40, 8.60] },
  medium: { tiles: 3, multipliers: [1.40, 2.05, 3.00, 4.40, 6.50, 9.80, 14.80, 22.50] },
  hard: { tiles: 2, multipliers: [1.90, 3.70, 7.30, 14.50, 28.50, 56.00, 110.00, 220.00] }
};

function initTowerUI() {
  const diff = $('towerDifficulty')?.value || 'medium';
  towerDifficulty = diff;
  const cfg = CLIENT_TOWER_CONFIGS[diff];
  towerMultipliers = cfg.multipliers;
  towerFloor = 0;
  towerActive = false;
  towerAwaitingCashout = false;

  $('towerFloorDisplay').textContent = '1';
  $('towerCoefDisplay').textContent = `(x${cfg.multipliers[0]})`;
  $('towerStatus').textContent = 'Выберите сложность, ставку и начните восхождение.';

  const dotsWrap = $('towerProgressDots');
  if (dotsWrap) {
    dotsWrap.innerHTML = Array.from({ length: 8 }, (_, i) => `<div class="tower-dot ${i === 0 ? 'current' : ''}"></div>`).join('');
  }

  renderTowerCurrentTiles(cfg.tiles, true);

  $('towerStartBtn')?.classList.remove('hidden');
  $('towerCashoutBtn')?.classList.add('hidden');
  $('towerDifficulty').disabled = false;
  restoreTowerState().catch(err => {
    $('towerStatus').textContent = err.message;
  });
}

async function restoreTowerState() {
  const data = await api('/api/games/tower/state');
  if (!data.active) {
    towerActive = false;
    $('towerDifficulty').disabled = false;
    return false;
  }

  towerDifficulty = data.difficulty;
  $('towerDifficulty').value = towerDifficulty;
  $('towerDifficulty').disabled = true;
  towerMultipliers = data.multipliers || CLIENT_TOWER_CONFIGS[towerDifficulty].multipliers;
  towerFloor = data.current_floor;
  towerAwaitingCashout = Boolean(data.completed);
  towerActive = !towerAwaitingCashout;
  updateTowerFloorDisplay(Math.min(towerFloor, 7));
  renderTowerCurrentTiles(data.tiles || CLIENT_TOWER_CONFIGS[towerDifficulty].tiles, towerAwaitingCashout);
  $('towerStartBtn').classList.add('hidden');
  $('towerCashoutBtn').classList.remove('hidden');
  $('towerCashoutBtn').disabled = !data.can_cashout;
  $('towerCashoutBtn').textContent = data.can_cashout
    ? `Забрать (x${towerMultipliers[towerFloor - 1]})`
    : 'Забрать выигрыш';
  $('towerStatus').textContent = towerAwaitingCashout
    ? '🎉 Башня пройдена! Нажмите «Забрать», чтобы получить выплату.'
    : data.can_cashout
      ? `Игра продолжается. Выберите дверь на этаже ${towerFloor + 1} или заберите выигрыш.`
      : 'Игра уже начата. Выберите дверь на первом этаже.';
  return true;
}

function renderTowerCurrentTiles(tilesCount, disabled = false) {
  const row = $('towerTilesRow');
  if (!row) return;
  row.innerHTML = Array.from({ length: tilesCount }, (_, t) => {
    return `<button class="tower-tile-btn" data-tile="${t}" ${disabled ? 'disabled' : ''}>❓</button>`;
  }).join('');

  if (!disabled) {
    row.querySelectorAll('.tower-tile-btn').forEach(btn => {
      btn.addEventListener('click', () => stepTower(Number(btn.dataset.tile)));
    });
  }
}

async function playTower() {
  if (towerActive) return;
  const startBtn = $('towerStartBtn');
  const cashoutBtn = $('towerCashoutBtn');
  startBtn.classList.add('hidden');
  cashoutBtn.classList.remove('hidden');
  cashoutBtn.disabled = true;
  $('towerStatus').textContent = 'Башня открыта! Сделайте ваш первый шаг.';

  towerDifficulty = $('towerDifficulty').value;
  const cfg = CLIENT_TOWER_CONFIGS[towerDifficulty];

  try {
    const data = await api('/api/games/tower/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        amount: Number($('towerAmount').value || 0),
        currency: $('towerCurrency').value,
        difficulty: towerDifficulty
      })
    });

    state.bootstrap.profile = data.profile;
    fillStats();

    towerActive = true;
    towerAwaitingCashout = false;
    towerFloor = 0;
    towerMultipliers = data.multipliers || cfg.multipliers;
    $('towerDifficulty').disabled = true;

    updateTowerFloorDisplay(0);
    renderTowerCurrentTiles(cfg.tiles, false);
  } catch(err) {
    if (err.message.toLowerCase().includes('уже начата')) {
      try {
        if (await restoreTowerState()) return;
      } catch (_) {}
    }
    $('towerStatus').textContent = err.message;
    towerActive = false;
    towerAwaitingCashout = false;
    $('towerDifficulty').disabled = false;
    startBtn.classList.remove('hidden');
    cashoutBtn.classList.add('hidden');
  }
}

function updateTowerFloorDisplay(floor) {
  $('towerFloorDisplay').textContent = `${floor + 1}`;
  const nextMul = towerMultipliers[floor] || 1;
  $('towerCoefDisplay').textContent = `(x${nextMul})`;

  const dots = document.querySelectorAll('.tower-dot');
  dots.forEach((dot, idx) => {
    dot.classList.remove('passed', 'current');
    if (idx < floor) dot.classList.add('passed');
    else if (idx === floor) dot.classList.add('current');
  });
}

async function stepTower(tileIndex) {
  if (!towerActive) return;
  const tiles = document.querySelectorAll('.tower-tile-btn');
  tiles.forEach(b => b.disabled = true);
  $('towerCashoutBtn').disabled = true;

  const clickedBtn = document.querySelector(`.tower-tile-btn[data-tile="${tileIndex}"]`);

  try {
    const data = await api('/api/games/tower/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, tile_index: tileIndex })
    });

    if (data.status === 'boom' || data.exploded) {
      if (clickedBtn) {
        clickedBtn.classList.add('mine');
        clickedBtn.textContent = '💣';
      }
      if (data.bomb_indices) {
        data.bomb_indices.forEach(bIdx => {
          const b = document.querySelector(`.tower-tile-btn[data-tile="${bIdx}"]`);
          if (b) { b.classList.add('revealed-mine'); b.textContent = '💣'; }
        });
      }
      $('towerStatus').textContent = '💥 Бум! Вы наступили на мину. Ставка сгорела.';
      towerActive = false;
      towerAwaitingCashout = false;
      $('towerDifficulty').disabled = false;
      $('towerStartBtn').classList.remove('hidden');
      $('towerCashoutBtn').classList.add('hidden');
    } else {
      if (clickedBtn) {
        clickedBtn.classList.add('safe');
        clickedBtn.textContent = '💎';
      }
      towerFloor = data.current_floor;

      if (data.status === 'won' || data.auto_cashout) {
        $('towerStatus').textContent = '🎉 Победа! Вы прошли всю башню. Нажмите «Забрать», чтобы получить выплату.';
        towerActive = false;
        towerAwaitingCashout = true;
        $('towerCashoutBtn').classList.remove('hidden');
        $('towerCashoutBtn').disabled = false;
        $('towerCashoutBtn').textContent = `Забрать (x${data.current_multiplier})`;
        document.querySelectorAll('.tower-tile-btn').forEach(button => { button.disabled = true; });
        updateTowerFloorDisplay(7);
      } else {
        $('towerStatus').textContent = `💎 Отлично! Множитель x${data.current_multiplier}. Заберите или идите выше!`;
        $('towerCashoutBtn').disabled = false;
        $('towerCashoutBtn').textContent = `Забрать (x${data.current_multiplier})`;

        await sleep(500);
        if (towerActive) {
          updateTowerFloorDisplay(towerFloor);
          renderTowerCurrentTiles(CLIENT_TOWER_CONFIGS[towerDifficulty].tiles, false);
        }
      }
    }

    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
  } catch(err) {
    $('towerStatus').textContent = err.message;
    tiles.forEach(b => b.disabled = false);
    $('towerCashoutBtn').disabled = (towerFloor === 0);
  }
}

async function cashoutTower() {
  if (!towerActive && !towerAwaitingCashout) return;
  $('towerCashoutBtn').disabled = true;
  document.querySelectorAll('.tower-tile-btn').forEach(b => b.disabled = true);

  try {
    const data = await api('/api/games/tower/cashout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData })
    });

    $('towerStatus').textContent = `💰 Вы забрали ${fmt(data.payout, 4)} с множителем x${data.multiplier}!`;
    towerActive = false;
    towerAwaitingCashout = false;
    $('towerDifficulty').disabled = false;
    $('towerStartBtn').classList.remove('hidden');
    $('towerCashoutBtn').classList.add('hidden');
    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
  } catch(err) {
    $('towerStatus').textContent = err.message;
    $('towerCashoutBtn').disabled = false;
  }
}

/* ==============================================================================
   BLACKJACK LOGIC
   ============================================================================== */
let bjActive = false;
let bjActionPending = false;
let bjPreviousHands = { player: [], dealer: [] };

function setBjActionPending(pending) {
  bjActionPending = pending;
  ['bjHitBtn', 'bjStandBtn', 'bjDoubleBtn'].forEach(id => {
    const button = $(id);
    if (button) button.disabled = pending;
  });
}

function restoreBjActionButtons() {
  setBjActionPending(false);
  $('bjHitBtn').disabled = false;
  $('bjStandBtn').disabled = false;
  $('bjDoubleBtn').disabled = $('bjPlayerCards').children.length !== 2;
}

function renderBjCard(cardStr, index, animation = '') {
  const animationClass = animation ? ` ${animation}` : '';
  const dealOrder = Math.min(index, 3);
  if (!cardStr || cardStr === '?') {
    return `<div class="bj-card hidden-card${animationClass}" style="--deal-order:${dealOrder}"><div class="bj-hidden-pattern">♠️</div></div>`;
  }
  const suitCode = cardStr.slice(-1);
  const rank = cardStr.slice(0, -1);
  const suitMap = { 'H': '♥️', 'D': '♦️', 'C': '♣️', 'S': '♠️' };
  const suit = suitMap[suitCode] || suitCode;
  const isRed = suitCode === 'H' || suitCode === 'D';
  const pipPositions = {
    2: [[50, 27], [50, 73]],
    3: [[50, 27], [50, 50], [50, 73]],
    4: [[30, 27], [70, 27], [30, 73], [70, 73]],
    5: [[30, 27], [70, 27], [50, 50], [30, 73], [70, 73]],
    6: [[30, 25], [70, 25], [30, 50], [70, 50], [30, 75], [70, 75]],
    7: [[30, 25], [70, 25], [30, 50], [50, 38], [70, 50], [30, 75], [70, 75]],
    8: [[30, 25], [70, 25], [30, 50], [50, 38], [70, 50], [50, 62], [30, 75], [70, 75]],
    9: [[30, 23], [50, 23], [70, 23], [30, 50], [50, 50], [70, 50], [30, 77], [50, 77], [70, 77]],
    10: [[30, 20], [70, 20], [50, 32], [30, 40], [70, 40], [30, 60], [70, 60], [50, 68], [30, 80], [70, 80]],
  };
  const isFace = ['J', 'Q', 'K'].includes(rank);
  const center = isFace
    ? `<div class="bj-card-face"><span class="bj-card-face-mark">${rank}</span><span class="bj-card-face-suit">${suit}</span><span class="bj-card-face-mark">${rank}</span></div>`
    : rank === 'A'
      ? `<div class="bj-card-ace">${suit}</div>`
      : `<div class="bj-card-pips">${(pipPositions[Number(rank)] || []).map(([left, top]) => `<span class="bj-card-pip${top > 50 ? ' bottom' : ''}" style="left:${left}%;top:${top}%">${suit}</span>`).join('')}</div>`;
  return `
    <div class="bj-card ${isRed ? 'red' : 'black'}${animationClass}" style="--deal-order:${dealOrder}">
      <div class="bj-card-corner">
        <span class="bj-card-rank">${rank}</span>
        <span class="bj-card-suit-small">${suit}</span>
      </div>
      ${center}
      <div class="bj-card-corner bottom">
        <span class="bj-card-rank">${rank}</span>
        <span class="bj-card-suit-small">${suit}</span>
      </div>
    </div>
  `;
}

function initBlackjackUI() {
  bjActive = false;
  bjActionPending = false;
  bjPreviousHands = { player: [], dealer: [] };
  $('bjPlayerCards').innerHTML = '';
  $('bjDealerCards').innerHTML = '';
  $('bjPlayerScore').textContent = 'Очки: —';
  $('bjDealerScore').textContent = 'Очки: —';
  $('bjDealBtn').classList.remove('hidden');
  $('bjDealBtn').textContent = 'Загрузка игры...';
  $('bjDealBtn').disabled = true;
  $('bjHitBtn').classList.add('hidden');
  $('bjStandBtn').classList.add('hidden');
  $('bjDoubleBtn').classList.add('hidden');
  $('bjStatus').textContent = 'Проверяем незавершённую раздачу...';
  restoreBlackjack().catch(err => {
    $('bjStatus').textContent = err.message;
    $('bjDealBtn').textContent = 'Раздать карты';
    $('bjDealBtn').disabled = false;
  });
}

async function restoreBlackjack() {
  const data = await api('/api/games/blackjack/state');
  if (data.active) {
    updateBjUI(data);
    return;
  }
  $('bjDealBtn').textContent = 'Раздать карты';
  $('bjDealBtn').disabled = false;
  $('bjStatus').textContent = 'Сделайте ставку и нажмите «Раздать карты».';
}

function updateBjUI(data) {
  if (!data) return;
  bjActionPending = false;

  const playerHand = data.player_hand || [];
  const dealerHand = data.dealer_hand || [];
  $('bjPlayerCards').innerHTML = playerHand.map((card, index) => {
    const animation = index >= bjPreviousHands.player.length ? 'dealing' : '';
    return renderBjCard(card, index, animation);
  }).join('');
  $('bjDealerCards').innerHTML = dealerHand.map((card, index) => {
    const isNew = index >= bjPreviousHands.dealer.length;
    const revealsHoleCard = bjPreviousHands.dealer[index] === '?' && card !== '?';
    return renderBjCard(card, index, isNew ? 'dealing' : revealsHoleCard ? 'revealing' : '');
  }).join('');
  bjPreviousHands = { player: [...playerHand], dealer: [...dealerHand] };

  const pScore = $('bjPlayerScore');
  const dScore = $('bjDealerScore');
  const st = data.status || 'playing';
  pScore.textContent = Number.isFinite(Number(data.player_score)) ? `Очки: ${data.player_score}` : 'Очки: —';
  const dealerScore = Number(data.dealer_score);
  dScore.textContent = Number.isFinite(dealerScore)
    ? `Очки: ${dealerScore}${st === 'playing' ? ' + ?' : ''}`
    : 'Очки: —';
  if (st === 'playing') {
    bjActive = true;
    $('bjStatus').textContent = 'Ваш ход. Возьмите карту, остановитесь или удвойте.';
    $('bjDealBtn').classList.add('hidden');
    $('bjHitBtn').classList.remove('hidden');
    $('bjStandBtn').classList.remove('hidden');
    $('bjDoubleBtn').classList.remove('hidden');
    $('bjHitBtn').disabled = false;
    $('bjStandBtn').disabled = false;
    $('bjDoubleBtn').disabled = data.can_double === false || (data.can_double == null && data.player_hand?.length !== 2);
  } else {
    bjActive = false;
    $('bjDealBtn').classList.remove('hidden');
    $('bjDealBtn').textContent = 'Сыграть ещё';
    $('bjHitBtn').classList.add('hidden');
    $('bjStandBtn').classList.add('hidden');
    $('bjDoubleBtn').classList.add('hidden');

    let res = 'Игра завершена.';
    if (st === 'player_blackjack') res = '🔥 Блэкджек! Выплата 3:2!';
    else if (st === 'dealer_blackjack') res = 'У дилера Блэкджек. Ставка проиграна.';
    else if (st === 'player_bust' || st === 'bust') res = '💥 Перебор (> 21). Вы проиграли.';
    else if (st === 'dealer_bust') res = '🎉 У дилера перебор! Вы выиграли!';
    else if (st === 'player_win' || st === 'win') res = '🎉 Вы выиграли!';
    else if (st === 'dealer_win' || st === 'loss') res = 'Дилер набрал больше. Вы проиграли.';
    else if (st === 'push') res = '🤝 Ничья (Push). Ставка возвращена.';

    if (data.payout > 0) res += ` Выплата: ${fmt(data.payout, 4)}`;
    $('bjStatus').textContent = res;
  }
}

async function playBlackjack() {
  if (bjActive) return;
  $('bjDealBtn').classList.add('hidden');
  $('bjStatus').textContent = 'Раздача карт...';

  try {
    const data = await api('/api/games/blackjack/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        amount: Number($('bjAmount').value || 0),
        currency: $('bjCurrency').value
      })
    });
    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
    updateBjUI(data);
  } catch(err) {
    $('bjStatus').textContent = err.message;
    $('bjDealBtn').classList.remove('hidden');
  }
}

async function hitBlackjack() {
  if (!bjActive || bjActionPending) return;
  setBjActionPending(true);
  try {
    const data = await api('/api/games/blackjack/hit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData })
    });
    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
    updateBjUI(data);
  } catch(err) {
    $('bjStatus').textContent = err.message;
    restoreBjActionButtons();
  }
}

async function standBlackjack() {
  if (!bjActive || bjActionPending) return;
  setBjActionPending(true);
  $('bjStatus').textContent = 'Ход дилера...';
  try {
    const data = await api('/api/games/blackjack/stand', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData })
    });
    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
    updateBjUI(data);
  } catch(err) {
    $('bjStatus').textContent = err.message;
    restoreBjActionButtons();
  }
}

async function doubleBlackjack() {
  if (!bjActive || bjActionPending) return;
  setBjActionPending(true);
  $('bjStatus').textContent = 'Удвоение ставки...';
  try {
    const data = await api('/api/games/blackjack/double', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData })
    });
    if (data.profile) state.bootstrap.profile = data.profile;
    fillStats();
    updateBjUI(data);
  } catch(err) {
    $('bjStatus').textContent = err.message;
    restoreBjActionButtons();
  }
}

/* ==========================================================================
   UPGRADE GAME (АПГРЕЙДЫ) LOGIC
   ========================================================================== */

const upgradeState = {
  mode: 'inventory',
  selectedInventoryGiftId: null,
  selectedTargetModel: null,
  starsAmount: 50,
  currentRotation: 0,
  isSpinning: false,
  rarityFilter: 'all',
};

function getUpgradeTargets() {
  if (Array.isArray(state.bootstrap?.upgrade_targets) && state.bootstrap.upgrade_targets.length > 0) {
    return state.bootstrap.upgrade_targets.map(item => resolveGiftValue(item));
  }
  const allTables = [CASE150_DROP_TABLE, CASE250_DROP_TABLE, CASE400_DROP_TABLE, CASE600_DROP_TABLE];
  const seen = {};
  for (const table of allTables) {
    for (const item of table) {
      if (item.kind !== 'gift' || !item.model) continue;
      const model = String(item.model).toLowerCase();
      if (!seen[model]) {
        seen[model] = resolveGiftValue(item);
      }
    }
  }
  return Object.values(seen).sort((a, b) => (Number(a.value) || 0) - (Number(b.value) || 0));
}

function initUpgradeUI() {
  const profile = state.bootstrap?.profile || {};
  const starsBalance = Math.floor(Number(profile.balance_stars ?? profile.total_stars ?? 0));
  if ($('upgradeUserStarsBalance')) $('upgradeUserStarsBalance').textContent = fmt(starsBalance, 0);

  const inventory = (Array.isArray(state.bootstrap?.inventory) ? state.bootstrap.inventory : []).filter(item => item.kind === 'gift' && !item.pending_withdraw);

  if (inventory.length === 0 && upgradeState.mode === 'inventory') {
    setUpgradeBetMode('stars');
  }

  if (!upgradeState.selectedTargetModel) {
    const targets = getUpgradeTargets();
    if (targets.length > 0) {
      // Pick an interesting default target like ufc-box or first item
      const preferred = targets.find(t => t.model === 'ufc-box') || targets[Math.min(3, targets.length - 1)];
      upgradeState.selectedTargetModel = preferred?.model || targets[0].model;
    }
  }

  renderUpgradeSelectedSlots();
  updateUpgradeCalculations();
}

function setUpgradeBetMode(mode) {
  if (upgradeState.isSpinning) return;
  upgradeState.mode = mode;
  if ($('upgradeModeNftBtn')) $('upgradeModeNftBtn').classList.toggle('active', mode === 'inventory');
  if ($('upgradeModeStarsBtn')) $('upgradeModeStarsBtn').classList.toggle('active', mode === 'stars');
  if ($('upgradeSourceNftBox')) $('upgradeSourceNftBox').classList.toggle('hidden', mode !== 'inventory');
  if ($('upgradeSourceStarsBox')) $('upgradeSourceStarsBox').classList.toggle('hidden', mode !== 'stars');
  updateUpgradeCalculations();
}

function onUpgradeStarsInput() {
  const input = $('upgradeStarsInput');
  if (!input) return;
  let val = Math.max(5, Math.min(10000, Math.floor(Number(input.value || 5))));
  upgradeState.starsAmount = val;
  updateUpgradeCalculations();
}

let _lastUpgradeChipClickTime = 0;
let _lastUpgradeChipAmount = 0;

function setUpgradeStarsAmount(amount) {
  if (upgradeState.isSpinning) return;
  const now = Date.now();
  if (now - _lastUpgradeChipClickTime < 100 && _lastUpgradeChipAmount === amount) {
    return;
  }
  _lastUpgradeChipClickTime = now;
  _lastUpgradeChipAmount = amount;

  const input = $('upgradeStarsInput');
  const current = Number(input?.value || 0);
  const next = Math.max(5, Math.min(10000, current + amount));
  if (input) input.value = next;
  upgradeState.starsAmount = next;
  updateUpgradeCalculations();
}

function setUpgradeStarsMax() {
  if (upgradeState.isSpinning) return;
  const profile = state.bootstrap?.profile || {};
  const starsBalance = Math.floor(Number(profile.balance_stars ?? profile.total_stars ?? 0));
  const maxBet = Math.max(5, Math.min(10000, starsBalance));
  const input = $('upgradeStarsInput');
  if (input) input.value = maxBet;
  upgradeState.starsAmount = maxBet;
  updateUpgradeCalculations();
}

function renderUpgradeSelectedSlots() {
  const inventory = Array.isArray(state.bootstrap?.inventory) ? state.bootstrap.inventory : [];
  const selectedItem = inventory.find(x => x.id === upgradeState.selectedInventoryGiftId && !x.pending_withdraw);

  const nftEmpty = $('upgradeSourceNftEmpty');
  const nftSelected = $('upgradeSourceNftSelected');

  if (selectedItem) {
    if (nftEmpty) nftEmpty.classList.add('hidden');
    if (nftSelected) {
      nftSelected.classList.remove('hidden');
      if ($('upgradeSourceNftImg')) $('upgradeSourceNftImg').src = getInventoryItemImage(selectedItem);
      if ($('upgradeSourceNftName')) $('upgradeSourceNftName').textContent = selectedItem.name || selectedItem.label || 'NFT Gift';
      const itemPrice = getLiveGiftStarsPrice(selectedItem);
      const rarity = getRarityByStars(itemPrice);
      if ($('upgradeSourceNftRarity')) {
        $('upgradeSourceNftRarity').textContent = rarity.charAt(0).toUpperCase() + rarity.slice(1);
        $('upgradeSourceNftRarity').className = `upgrade-rarity-badge ${rarity}`;
      }
      if ($('upgradeSourceNftValue')) $('upgradeSourceNftValue').textContent = fmt(itemPrice, 0);
    }
  } else {
    upgradeState.selectedInventoryGiftId = null;
    if (nftEmpty) nftEmpty.classList.remove('hidden');
    if (nftSelected) nftSelected.classList.add('hidden');
  }

  const targets = getUpgradeTargets();
  const selectedTarget = targets.find(x => String(x.model || '').toLowerCase() === String(upgradeState.selectedTargetModel || '').toLowerCase());

  const targetEmpty = $('upgradeTargetEmpty');
  const targetSelected = $('upgradeTargetSelected');

  if (selectedTarget) {
    if (targetEmpty) targetEmpty.classList.add('hidden');
    if (targetSelected) {
      targetSelected.classList.remove('hidden');
      if ($('upgradeTargetImg')) $('upgradeTargetImg').src = getRewardImage(selectedTarget);
      if ($('upgradeTargetName')) $('upgradeTargetName').textContent = selectedTarget.name || selectedTarget.label || 'NFT Gift';
      const targetPrice = getLiveGiftStarsPrice(selectedTarget);
      const rarity = getRarityByStars(targetPrice);
      if ($('upgradeTargetRarity')) {
        $('upgradeTargetRarity').textContent = rarity.charAt(0).toUpperCase() + rarity.slice(1);
        $('upgradeTargetRarity').className = `upgrade-rarity-badge ${rarity}`;
      }
      if ($('upgradeTargetValue')) $('upgradeTargetValue').textContent = fmt(targetPrice, 0);
    }
  } else {
    if (targetEmpty) targetEmpty.classList.remove('hidden');
    if (targetSelected) targetSelected.classList.add('hidden');
  }
}

function getUpgradeBetValue() {
  if (upgradeState.mode === 'inventory') {
    const inventory = Array.isArray(state.bootstrap?.inventory) ? state.bootstrap.inventory : [];
    const item = inventory.find(x => x.id === upgradeState.selectedInventoryGiftId && !x.pending_withdraw);
    return item ? getLiveGiftStarsPrice(item) : 0;
  }
  const inputVal = Number($('upgradeStarsInput')?.value || upgradeState.starsAmount || 0);
  return Math.max(0, inputVal);
}

function getUpgradeTargetValue() {
  const targets = getUpgradeTargets();
  const item = targets.find(x => String(x.model || '').toLowerCase() === String(upgradeState.selectedTargetModel || '').toLowerCase());
  return item ? getLiveGiftStarsPrice(item) : 0;
}

function updateUpgradeCalculations() {
  renderUpgradeSelectedSlots();

  const profile = state.bootstrap?.profile || {};
  const userBalance = Math.floor(Number(profile.balance_stars ?? profile.total_stars ?? 0));
  if ($('upgradeUserStarsBalance')) $('upgradeUserStarsBalance').textContent = fmt(userBalance, 0);

  const betValue = getUpgradeBetValue();
  const targetValue = getUpgradeTargetValue();

  if ($('upgradeSourceTotalDisplay')) $('upgradeSourceTotalDisplay').textContent = `${fmt(betValue, 0)} ⭐`;
  if ($('upgradeTargetTotalDisplay')) $('upgradeTargetTotalDisplay').textContent = `${fmt(targetValue, 0)} ⭐`;

  const wheelFace = $('upgradeWheel');
  const percentEl = $('upgradeWheelPercent');
  const multEl = $('upgradeWheelMultiplier');
  const statusEl = $('upgradeStatusText');
  const spinBtn = $('upgradeSpinBtn');
  const spinLabel = $('upgradeSpinBtnLabel');

  if (upgradeState.isSpinning) {
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'Крутится...';
    return;
  }

  if (upgradeState.mode === 'inventory' && !upgradeState.selectedInventoryGiftId) {
    if (wheelFace) wheelFace.style.background = 'conic-gradient(from 0deg, #10b981 0deg 0deg, #1a1e36 0deg 360deg)';
    if (percentEl) percentEl.textContent = '0.00%';
    if (multEl) multEl.textContent = 'x0.00';
    if (statusEl) {
      statusEl.className = 'upgrade-status-text';
      statusEl.textContent = 'Выберите NFT из инвентаря для ставки';
    }
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'ВЫБЕРИТЕ СТАВКУ';
    return;
  }

  if (upgradeState.mode === 'stars' && betValue < 5) {
    if (wheelFace) wheelFace.style.background = 'conic-gradient(from 0deg, #10b981 0deg 0deg, #1a1e36 0deg 360deg)';
    if (percentEl) percentEl.textContent = '0.00%';
    if (multEl) multEl.textContent = 'x0.00';
    if (statusEl) {
      statusEl.className = 'upgrade-status-text';
      statusEl.textContent = 'Минимальная ставка — 5 звёзд';
    }
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'СТАВКА ОТ 5 ⭐';
    return;
  }

  if (upgradeState.mode === 'stars' && betValue > userBalance) {
    if (statusEl) {
      statusEl.className = 'upgrade-status-text lose';
      statusEl.textContent = `Недостаточно Stars (баланс ${fmt(userBalance, 0)} ⭐)`;
    }
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'НЕДОСТАТОЧНО STARS';
    return;
  }

  if (!upgradeState.selectedTargetModel || targetValue <= 0) {
    if (wheelFace) wheelFace.style.background = 'conic-gradient(from 0deg, #10b981 0deg 0deg, #1a1e36 0deg 360deg)';
    if (percentEl) percentEl.textContent = '0.00%';
    if (multEl) multEl.textContent = 'x0.00';
    if (statusEl) {
      statusEl.className = 'upgrade-status-text';
      statusEl.textContent = 'Выберите желаемый NFT из каталога';
    }
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'ВЫБЕРИТЕ ЦЕЛЬ';
    return;
  }

  if (betValue >= targetValue) {
    if (wheelFace) wheelFace.style.background = 'conic-gradient(from 0deg, #10b981 0deg 0deg, #1a1e36 0deg 360deg)';
    if (percentEl) percentEl.textContent = '0.00%';
    if (multEl) multEl.textContent = 'x0.00';
    if (statusEl) {
      statusEl.className = 'upgrade-status-text lose';
      statusEl.textContent = `Цель (${targetValue} ⭐) должна быть дороже ставки (${betValue} ⭐)`;
    }
    if (spinBtn) spinBtn.disabled = true;
    if (spinLabel) spinLabel.textContent = 'ЦЕЛЬ ДЕШЕВЛЕ СТАВКИ';
    return;
  }

  const realChance = (betValue / targetValue) * 100.0;
  const rtp = (Number(state.bootstrap?.pricing?.game_rtp_percent?.upgrade || 95)) / 100.0;
  const rtpChance = realChance * rtp;
  const effectiveChance = Math.max(realChance, rtpChance);
  const chance = Math.max(1.0, Math.min(95.0, Number(effectiveChance.toFixed(2))));
  const multiplier = Number((targetValue / betValue).toFixed(2));
  const winAngle = (chance / 100.0) * 360.0;

  if (wheelFace) {
    wheelFace.style.background = `conic-gradient(from 0deg, #10b981 0deg ${winAngle}deg, #1a1e36 ${winAngle}deg 360deg)`;
  }
  if (percentEl) percentEl.textContent = `${chance.toFixed(2)}%`;
  if (multEl) multEl.textContent = `x${multiplier.toFixed(2)}`;
  if (statusEl) {
    statusEl.className = 'upgrade-status-text';
    statusEl.textContent = `Шанс выиграть: ${chance.toFixed(2)}% • Множитель: x${multiplier.toFixed(2)}`;
  }
  if (spinBtn) spinBtn.disabled = false;
  if (spinLabel) spinLabel.textContent = `СДЕЛАТЬ АПГРЕЙД (${chance.toFixed(1)}%)`;
}

function clearUpgradeBet(event) {
  if (event) event.stopPropagation();
  if (upgradeState.isSpinning) return;
  upgradeState.selectedInventoryGiftId = null;
  updateUpgradeCalculations();
}

function clearUpgradeTarget(event) {
  if (event) event.stopPropagation();
  if (upgradeState.isSpinning) return;
  upgradeState.selectedTargetModel = null;
  updateUpgradeCalculations();
}

/* Modals */
function openUpgradeInventoryModal() {
  if (upgradeState.isSpinning) return;
  const modal = $('upgradeInventoryModal');
  const list = $('upgradeInventoryModalList');
  if (!modal || !list) return;

  const inventory = (Array.isArray(state.bootstrap?.inventory) ? state.bootstrap.inventory : []).filter(item => item.kind === 'gift' && !item.pending_withdraw);

  if (!inventory.length) {
    list.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 24px 12px; color: var(--hint);">
        <div style="font-size: 36px; margin-bottom: 8px;">🧩</div>
        <strong style="color: #e2e8f0; font-size: 15px;">В инвентаре пока нет NFT</strong>
        <p style="font-size: 13px; margin-top: 6px;">Откройте кейсы или сделайте ставку звёздами Stars ⭐</p>
        <button type="button" class="primary small" style="margin-top: 14px;" id="upgradeModalToStarsBtn">Поставить Stars</button>
      </div>
    `;
    list.querySelector('#upgradeModalToStarsBtn')?.addEventListener('click', () => {
      closeUpgradeInventoryModal();
      setUpgradeBetMode('stars');
    });
  } else {
    list.innerHTML = inventory.map(item => {
      const price = getLiveGiftStarsPrice(item);
      const isSelected = item.id === upgradeState.selectedInventoryGiftId;
      const rarity = getRarityByStars(price);
      return `
        <div class="upgrade-target-card-item ${isSelected ? 'selected' : ''}" data-select-gift="${item.id}" onclick="selectUpgradeInventoryGift('${item.id}')">
          <img src="${getInventoryItemImage(item)}" alt="${item.name || item.label}" onerror="this.onerror=null;this.src='${getInventoryItemImageErrorFallback(item)}'" />
          <span class="upgrade-rarity-badge ${rarity}">${rarity.charAt(0).toUpperCase() + rarity.slice(1)}</span>
          <strong class="upgrade-item-title" style="margin-top: 4px;">${item.name || item.label}</strong>
          <div class="upgrade-item-val">${fmt(price, 0)} ⭐</div>
        </div>
      `;
    }).join('');

    list.querySelectorAll('[data-select-gift]').forEach(card => {
      card.addEventListener('click', () => {
        const giftId = card.getAttribute('data-select-gift');
        if (giftId) selectUpgradeInventoryGift(giftId);
      });
    });
  }

  modal.classList.remove('hidden');
}

function closeUpgradeInventoryModal() {
  $('upgradeInventoryModal')?.classList.add('hidden');
}

function selectUpgradeInventoryGift(giftId) {
  upgradeState.selectedInventoryGiftId = giftId;
  closeUpgradeInventoryModal();
  updateUpgradeCalculations();
}

async function openUpgradeTargetModal() {
  if (upgradeState.isSpinning) return;
  const modal = $('upgradeTargetModal');
  if (!modal) return;

  if (!Array.isArray(state.bootstrap?.upgrade_targets) || state.bootstrap.upgrade_targets.length === 0) {
    try {
      const data = await api('/api/games/upgrade/targets');
      if (Array.isArray(data?.targets) && data.targets.length > 0) {
        if (!state.bootstrap) state.bootstrap = {};
        state.bootstrap.upgrade_targets = data.targets;
      }
    } catch (e) {
      console.warn('Failed to load upgrade targets:', e);
    }
  }

  renderUpgradeTargetModalList();
  modal.classList.remove('hidden');
}

function closeUpgradeTargetModal() {
  $('upgradeTargetModal')?.classList.add('hidden');
}

function filterUpgradeTargets(rarity) {
  upgradeState.rarityFilter = rarity;
  document.querySelectorAll('.upgrade-chip-filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.rarity === rarity);
  });
  renderUpgradeTargetModalList();
}

function renderUpgradeTargetModalList() {
  const list = $('upgradeTargetModalList');
  if (!list) return;

  const betValue = getUpgradeBetValue();
  let targets = getUpgradeTargets();

  if (upgradeState.rarityFilter && upgradeState.rarityFilter !== 'all') {
    targets = targets.filter(x => getRarityByStars(getLiveGiftStarsPrice(x)).toLowerCase() === upgradeState.rarityFilter.toLowerCase());
  }

  if (!targets.length) {
    list.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 24px 12px; color: var(--hint);">
        <p>Подарки не найдены</p>
      </div>
    `;
    return;
  }

  const rtp = (Number(state.bootstrap?.pricing?.game_rtp_percent?.upgrade || 95)) / 100.0;

  list.innerHTML = targets.map(item => {
    const price = getLiveGiftStarsPrice(item);
    const isSelected = String(item.model || '').toLowerCase() === String(upgradeState.selectedTargetModel || '').toLowerCase();
    const isTooCheap = betValue > 0 && price <= betValue;
    const rarity = getRarityByStars(price);

    let chanceBadge = '';
    if (betValue > 0) {
      if (isTooCheap) {
        chanceBadge = `<span class="upgrade-card-chance-badge impossible">Дешевле ставки</span>`;
      } else {
        const realChance = (betValue / price) * 100.0;
        const rtpChance = realChance * rtp;
        const effectiveChance = Math.max(realChance, rtpChance);
        const chance = Math.max(1.0, Math.min(95.0, Number(effectiveChance.toFixed(1))));
        chanceBadge = `<span class="upgrade-card-chance-badge">${chance.toFixed(1)}%</span>`;
      }
    }

    return `
      <div class="upgrade-target-card-item ${isSelected ? 'selected' : ''} ${isTooCheap ? 'disabled' : ''}" 
           data-select-target="${item.model}" 
           data-disabled="${isTooCheap ? 'true' : 'false'}"
           onclick="${isTooCheap ? '' : `selectUpgradeTarget('${item.model}')`}">
        <img src="${getRewardImage(item)}" alt="${item.name || item.label}" onerror="this.onerror=null;this.src='${getRewardImageErrorFallback(item)}'" />
        <span class="upgrade-rarity-badge ${rarity}">${rarity.charAt(0).toUpperCase() + rarity.slice(1)}</span>
        <strong class="upgrade-item-title" style="margin-top: 4px;">${item.name || item.label}</strong>
        <div class="upgrade-item-val">${fmt(price, 0)} ⭐</div>
        ${chanceBadge}
      </div>
    `;
  }).join('');

  list.querySelectorAll('[data-select-target]').forEach(card => {
    card.addEventListener('click', () => {
      if (card.getAttribute('data-disabled') === 'true') return;
      const model = card.getAttribute('data-select-target');
      if (model) selectUpgradeTarget(model);
    });
  });
}

function selectUpgradeTarget(model) {
  upgradeState.selectedTargetModel = model;
  closeUpgradeTargetModal();
  updateUpgradeCalculations();
}

function openUpgradeWinModal(wonItem) {
  const modal = $('upgradeWinModal');
  if (!modal || !wonItem) return;
  if ($('upgradeWinImg')) $('upgradeWinImg').src = getRewardImage(wonItem);
  if ($('upgradeWinName')) $('upgradeWinName').textContent = wonItem.name || wonItem.label || 'NFT Gift';
  const winPrice = getLiveGiftStarsPrice(wonItem);
  const rarity = getRarityByStars(winPrice);
  if ($('upgradeWinRarity')) {
    $('upgradeWinRarity').textContent = rarity.charAt(0).toUpperCase() + rarity.slice(1);
    $('upgradeWinRarity').className = `upgrade-rarity-badge ${rarity}`;
  }
  if ($('upgradeWinValue')) $('upgradeWinValue').textContent = fmt(winPrice, 0);
  modal.classList.remove('hidden');
}

function closeUpgradeWinModal() {
  $('upgradeWinModal')?.classList.add('hidden');
}

function startUpgradeWithItem(giftId) {
  openGame('upgrade');
  setUpgradeBetMode('inventory');
  selectUpgradeInventoryGift(giftId);
}

/* Play Upgrade */
async function playUpgrade() {
  if (upgradeState.isSpinning) return;

  const betValue = getUpgradeBetValue();
  const targetValue = getUpgradeTargetValue();

  if (upgradeState.mode === 'inventory' && !upgradeState.selectedInventoryGiftId) {
    toast('Выберите NFT из инвентаря', 'warn');
    return;
  }
  if (upgradeState.mode === 'stars' && betValue < 5) {
    toast('Минимальная ставка — 5 звёзд', 'warn');
    return;
  }
  if (!upgradeState.selectedTargetModel) {
    toast('Выберите подарок для апгрейда', 'warn');
    return;
  }
  if (betValue >= targetValue) {
    toast('Цель должна быть дороже ставки', 'warn');
    return;
  }

  upgradeState.isSpinning = true;
  updateUpgradeCalculations();

  const spinBtn = $('upgradeSpinBtn');
  const spinLabel = $('upgradeSpinBtnLabel');
  const statusEl = $('upgradeStatusText');
  const wheelFace = $('upgradeWheel');
  const wheelRim = $('upgradeWheelRim');
  const pointer = $('upgradeWheelPointer');

  if (spinBtn) spinBtn.disabled = true;
  if (spinLabel) spinLabel.textContent = 'Крутится...';
  if (statusEl) {
    statusEl.className = 'upgrade-status-text';
    statusEl.textContent = 'Колесо вращается...';
  }
  if (wheelRim) wheelRim.classList.remove('win-glow', 'lose-glow');

  try {
    const payload = {
      init_data: state.initData,
      mode: upgradeState.mode,
      gift_id: upgradeState.mode === 'inventory' ? upgradeState.selectedInventoryGiftId : null,
      stars_amount: upgradeState.mode === 'stars' ? betValue : null,
      target_model: upgradeState.selectedTargetModel,
    };

    const data = await api('/api/games/upgrade/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // Landing calculations
    const winAngle = (data.win_chance_percent / 100.0) * 360.0;
    let landingAngle = 0;
    if (data.win) {
      landingAngle = (data.roll / data.win_chance_percent) * Math.max(1, winAngle - 4) + 2;
    } else {
      landingAngle = winAngle + 2 + ((data.roll - data.win_chance_percent) / Math.max(0.01, 100 - data.win_chance_percent)) * Math.max(1, 360 - winAngle - 4);
    }

    const currentMod = ((upgradeState.currentRotation % 360) + 360) % 360;
    const targetMod = ((360 - landingAngle) % 360 + 360) % 360;
    let delta = targetMod - currentMod;
    if (delta <= 0) delta += 360;

    const fullSpins = 360 * 5;
    const totalRotation = upgradeState.currentRotation + fullSpins + delta;
    upgradeState.currentRotation = totalRotation;

    if (wheelFace) {
      wheelFace.style.transition = 'transform 4.2s cubic-bezier(0.12, 0.88, 0.2, 1)';
      wheelFace.style.transform = `rotate(${totalRotation}deg)`;
    }

    if (pointer) pointer.classList.add('ticking');
    try {
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium');
    } catch (_) {}

    await sleep(4300);

    if (pointer) pointer.classList.remove('ticking');

    if (data.profile) state.bootstrap.profile = data.profile;
    if (data.games) state.bootstrap.games = data.games;
    if (Array.isArray(data.inventory)) state.bootstrap.inventory = data.inventory;

    fillStats();
    renderInventory();

    if (data.win) {
      if (wheelRim) wheelRim.classList.add('win-glow');
      if (statusEl) {
        statusEl.className = 'upgrade-status-text win';
        statusEl.textContent = `🎉 ПОБЕДА! Вы выиграли ${data.won_item?.label || 'NFT'}!`;
      }
      try {
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      } catch (_) {}
      openUpgradeWinModal(data.won_item);
    } else {
      if (wheelRim) wheelRim.classList.add('lose-glow');
      if (statusEl) {
        statusEl.className = 'upgrade-status-text lose';
        statusEl.textContent = `❌ Апгрейд не удался (${data.roll}% при шансе ${data.win_chance_percent}%).`;
      }
      try {
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
      } catch (_) {}
    }

    if (upgradeState.mode === 'inventory') {
      upgradeState.selectedInventoryGiftId = null;
    }
  } catch (err) {
    if (statusEl) {
      statusEl.className = 'upgrade-status-text lose';
      statusEl.textContent = err.message || 'Ошибка апгрейда';
    }
    toast(err.message || 'Ошибка апгрейда', 'error');
  } finally {
    upgradeState.isSpinning = false;
    updateUpgradeCalculations();
  }
}

function bind() {
  document.querySelectorAll('[data-open-game]').forEach(btn => btn.addEventListener('click', () => openGame(btn.dataset.openGame)));
  document.querySelectorAll('[data-open-tab]').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.openTab)));
  $('closeGameScreenBtn')?.addEventListener('click', closeGame);

  document.addEventListener('click', (e) => {
    const chipBtn = e.target.closest('.chip-btn');
    if (chipBtn) {
      if (chipBtn.classList.contains('chip-max') || chipBtn.dataset.max === 'true' || chipBtn.textContent.trim() === 'MAX') {
        setUpgradeStarsMax();
      } else {
        const val = Number(chipBtn.dataset.amount || (chipBtn.textContent || '').replace('+', '').trim());
        if (Number.isFinite(val) && val > 0) setUpgradeStarsAmount(val);
      }
      return;
    }
    const modeBtn = e.target.closest('.upgrade-mode-btn');
    if (modeBtn) {
      const mode = modeBtn.id === 'upgradeModeStarsBtn' || (modeBtn.textContent || '').includes('Stars') ? 'stars' : 'inventory';
      setUpgradeBetMode(mode);
      return;
    }
    const shopSubtabBtn = e.target.closest('.shop-subtab');
    if (shopSubtabBtn) {
      const isNft = shopSubtabBtn.id === 'shopSubtabNft' || shopSubtabBtn.dataset.shopSubtab === 'nft' || (shopSubtabBtn.textContent || '').includes('NFT');
      switchShopSubtab(isNft ? 'nft' : 'stars');
      return;
    }
    const rarityPill = e.target.closest('.nft-rarity-pill');
    if (rarityPill && rarityPill.dataset.rarity) {
      setNftShopRarity(rarityPill.dataset.rarity);
      return;
    }
    const adminBtn = e.target.closest('.admin-subtab');
    if (adminBtn) {
      const tabName = adminBtn.getAttribute('data-admin-tab');
      if (tabName) switchAdminTab(tabName);
      return;
    }
    const tabBtn = e.target.closest('.tab');
    if (tabBtn && tabBtn.dataset.tab) {
      switchTab(tabBtn.dataset.tab);
      return;
    }
  });

  $('topupStarsBtn')?.addEventListener('click', () => {
    switchTab('shop');
    setTimeout(() => {
      const el = $('starsAmount') || $('shopStarsCard');
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      $('starsAmount')?.focus();
    }, 120);
  });

  $('topupTonBtn')?.addEventListener('click', () => {
    switchTab('shop');
    setTimeout(() => {
      const el = $('tonAmount') || $('shopTonCard');
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      $('tonAmount')?.focus();
    }, 120);
  });

  $('starsTargetMode').addEventListener('change', () => $('starsTargetWrap').classList.toggle('hidden', $('starsTargetMode').value !== 'friend'));
  $('refreshBtn').addEventListener('click', () => loadBootstrap().catch(e => toast(e.message, 'error')));
  if ($('openInventoryBtn')) $('openInventoryBtn').addEventListener('click', () => switchTab('inventory'));
  $('reloadHistoryBtn').addEventListener('click', () => loadBootstrap().catch(e => toast(e.message, 'error')));

  $('starsPreviewBtn').addEventListener('click', () => previewStars().catch(e => toast(e.message, 'error')));
  $('starsOrderBtn').addEventListener('click', () => createStarsOrder().catch(e => toast(e.message, 'error')));
  $('premiumPreviewBtn').addEventListener('click', () => previewPremium().catch(e => toast(e.message, 'error')));
  $('premiumOrderBtn').addEventListener('click', () => createPremiumOrder().catch(e => toast(e.message, 'error')));
  $('tonPreviewBtn').addEventListener('click', () => previewTon().catch(e => toast(e.message, 'error')));
  $('tonOrderBtn').addEventListener('click', () => createTonOrder().catch(e => toast(e.message, 'error')));

  $('withdrawStarsBtn').addEventListener('click', () => createWithdraw('stars', Number($('withdrawStarsAmount').value || 0)).catch(e => toast(e.message, 'error')));
  $('withdrawTonBtn').addEventListener('click', () => createWithdraw('ton', Number($('withdrawTonAmount').value || 0)).catch(e => toast(e.message, 'error')));
  $('promoApplyBtn').addEventListener('click', () => applyPromo().catch(e => toast(e.message, 'error')));
  if ($('supportSendBtn')) $('supportSendBtn').addEventListener('click', () => sendSupport('support', $('supportText').value.trim()).catch(e => toast(e.message, 'error')));
  if ($('suggestionSendBtn')) $('suggestionSendBtn').addEventListener('click', () => sendSupport('suggestion', $('suggestionText').value.trim()).catch(e => toast(e.message, 'error')));
  if ($('reloadReviewsBtn')) $('reloadReviewsBtn').addEventListener('click', () => reloadReviews().catch(e => toast(e.message, 'error')));
  if ($('sendReviewBtn')) $('sendReviewBtn').addEventListener('click', () => sendReview().catch(e => toast(e.message, 'error')));

  if ($('roulettePlayBtn')) $('roulettePlayBtn').addEventListener('click', () => playRoulette().catch(e => toast(e.message, 'error')));
  if ($('minesStartBtn')) $('minesStartBtn').addEventListener('click', () => startMines().catch(e => toast(e.message, 'error')));
  if ($('minesCashoutBtn')) $('minesCashoutBtn').addEventListener('click', () => cashoutMines().catch(e => toast(e.message, 'error')));
  if ($('coinPlayBtn')) $('coinPlayBtn').addEventListener('click', () => playCoin().catch(e => toast(e.message, 'error')));
  if ($('crashPlayBtn')) $('crashPlayBtn').addEventListener('click', () => playCrash().catch(e => toast(e.message, 'error')));
  if ($('crashCashoutBtn')) $('crashCashoutBtn').addEventListener('click', () => cashoutCrash().catch(e => toast(e.message, 'error')));

  if ($('plinkoPlayBtn')) $('plinkoPlayBtn').addEventListener('click', () => playPlinko().catch(e => toast(e.message, 'error')));
  if ($('towerStartBtn')) $('towerStartBtn').addEventListener('click', () => playTower().catch(e => toast(e.message, 'error')));
  if ($('towerCashoutBtn')) $('towerCashoutBtn').addEventListener('click', () => cashoutTower().catch(e => toast(e.message, 'error')));
  if ($('bjDealBtn')) $('bjDealBtn').addEventListener('click', () => playBlackjack().catch(e => toast(e.message, 'error')));
  if ($('bjHitBtn')) $('bjHitBtn').addEventListener('click', () => hitBlackjack().catch(e => toast(e.message, 'error')));
  if ($('bjStandBtn')) $('bjStandBtn').addEventListener('click', () => standBlackjack().catch(e => toast(e.message, 'error')));
  if ($('bjDoubleBtn')) $('bjDoubleBtn').addEventListener('click', () => doubleBlackjack().catch(e => toast(e.message, 'error')));

  $('plinkoRows')?.addEventListener('change', () => drawPlinkoBoard());
  $('plinkoRisk')?.addEventListener('change', () => drawPlinkoBoard());
  $('plinkoAmount')?.addEventListener('input', () => updatePlinkoBallHint());
  $('plinkoBalls')?.addEventListener('change', () => updatePlinkoBallHint());
  $('plinkoCurrency')?.addEventListener('change', () => updatePlinkoBallHint());
  window.addEventListener('resize', () => {
    if (state.activeGame === 'plinko' && !plinkoActive) drawPlinkoBoard();
  });
  $('towerDifficulty')?.addEventListener('change', () => initTowerUI());

  document.querySelectorAll('.case-open-btn').forEach(btn => btn.addEventListener('click', () => openCase(btn.dataset.case).catch(e => toast(e.message, 'error'))));
  document.querySelectorAll('[data-upgrade]').forEach(card => {
    const button = card.querySelector('button');
    if (button) {
      button.addEventListener('click', () => buyUpgrade(card.dataset.upgrade).catch(e => toast(e.message, 'error')));
    }
  });

  if ($('submitProofBtn')) $('submitProofBtn').addEventListener('click', () => uploadProof().catch(e => toast(e.message, 'error')));
  if ($('closeProofModalBtn')) $('closeProofModalBtn').addEventListener('click', () => { if (!state.isUploadingProof) setProofModal(false); });
  if ($('cancelProofBtn')) $('cancelProofBtn').addEventListener('click', () => { if (!state.isUploadingProof) setProofModal(false); });

  const dropzone = $('proofDropzone');
  const fileInput = $('proofFile');
  if (dropzone && fileInput) {
    $('proofChangeFileBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      clearProofFile();
      try { fileInput.click(); } catch (_) {}
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        handleProofFileSelect(fileInput.files[0]);
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer?.files?.[0]) {
        handleProofFileSelect(e.dataTransfer.files[0]);
      }
    });
  }

  window.addEventListener('paste', (e) => {
    const modal = $('proofModal');
    if (!modal || modal.classList.contains('hidden')) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type && items[i].type.startsWith('image/')) {
        const blob = items[i].getAsFile();
        if (blob) {
          const file = new File([blob], `receipt_${Date.now()}.png`, { type: blob.type });
          handleProofFileSelect(file);
          toast('Чек вставлен из буфера обмена!', 'success');
          break;
        }
      }
    }
  });

  if ($('adminReloadBtn')) $('adminReloadBtn').addEventListener('click', () => loadAdminDashboard().catch(e => toast(e.message, 'error')));
  if ($('adminSaveStarPackagesBtn')) $('adminSaveStarPackagesBtn').addEventListener('click', () => adminSaveStarPackages().catch(e => toast(e.message, 'error')));
  if ($('adminSavePremiumBtn')) $('adminSavePremiumBtn').addEventListener('click', () => adminSavePremiumPrices().catch(e => toast(e.message, 'error')));
  if ($('adminSaveNftPricesBtn')) $('adminSaveNftPricesBtn').addEventListener('click', () => adminSaveNftPrices().catch(e => toast(e.message, 'error')));
  if ($('adminSaveNftImagesBtn')) $('adminSaveNftImagesBtn').addEventListener('click', () => adminSaveNftImages().catch(e => toast(e.message, 'error')));
  if ($('adminSaveNftCaseChancesBtn')) $('adminSaveNftCaseChancesBtn').addEventListener('click', () => adminSaveNftCaseChances().catch(e => toast(e.message, 'error')));
  if ($('adminSaveRtpBtn')) $('adminSaveRtpBtn').addEventListener('click', () => adminSaveGameRtp().catch(e => toast(e.message, 'error')));
  if ($('adminSaveCoinSettingsBtn')) $('adminSaveCoinSettingsBtn').addEventListener('click', () => adminSaveCoinSettings().catch(e => toast(e.message, 'error')));
  if ($('adminCreatePromoBtn')) $('adminCreatePromoBtn').addEventListener('click', () => adminCreatePromocode().catch(e => toast(e.message, 'error')));
  if ($('adminTrackBtn')) $('adminTrackBtn').addEventListener('click', () => adminTrackUser().catch(e => toast(e.message, 'error')));
  if ($('adminResetMinesBtn')) $('adminResetMinesBtn').addEventListener('click', () => adminResetTrackedUserMines().catch(e => toast(e.message, 'error')));
  if ($('adminResetAllGamesBtn')) $('adminResetAllGamesBtn').addEventListener('click', () => adminResetTrackedUserAllGames().catch(e => toast(e.message, 'error')));
  if ($('adminBroadcastBtn')) $('adminBroadcastBtn').addEventListener('click', () => adminSendBroadcast().catch(e => toast(e.message, 'error')));
  if ($('adminClearStatsBtn')) $('adminClearStatsBtn').addEventListener('click', () => adminClearGameStats().catch(e => toast(e.message, 'error')));
  if ($('adminRejectAllPendingBtn')) $('adminRejectAllPendingBtn').addEventListener('click', () => adminRejectAllPending().catch(e => toast(e.message, 'error')));
  if ($('adminAddNewNftBtn')) $('adminAddNewNftBtn').addEventListener('click', () => adminAddNewNftGift().catch(e => toast(e.message, 'error')));

  // Upgrade Game listeners
  $('upgradeModeNftBtn')?.addEventListener('click', () => setUpgradeBetMode('inventory'));
  $('upgradeModeStarsBtn')?.addEventListener('click', () => setUpgradeBetMode('stars'));
  $('upgradeStarsInput')?.addEventListener('input', onUpgradeStarsInput);
  $('upgradeSourceNftEmpty')?.addEventListener('click', openUpgradeInventoryModal);
  $('upgradeSourceNftSelected')?.addEventListener('click', openUpgradeInventoryModal);
  $('upgradeTargetEmpty')?.addEventListener('click', openUpgradeTargetModal);
  $('upgradeTargetSelected')?.addEventListener('click', openUpgradeTargetModal);
  $('upgradeOpenTargetModalBtn')?.addEventListener('click', openUpgradeTargetModal);
  $('closeUpgradeInventoryModalBtn')?.addEventListener('click', closeUpgradeInventoryModal);
  $('closeUpgradeTargetModalBtn')?.addEventListener('click', closeUpgradeTargetModal);
  $('upgradeWinCloseBtn')?.addEventListener('click', closeUpgradeWinModal);
  $('upgradeWinInventoryBtn')?.addEventListener('click', () => {
    closeUpgradeWinModal();
    closeGame();
    switchTab('inventory');
  });
  $('upgradeSpinBtn')?.addEventListener('click', playUpgrade);

  $('upgradeInventoryModal')?.addEventListener('click', (e) => {
    if (e.target === $('upgradeInventoryModal')) closeUpgradeInventoryModal();
  });
  $('upgradeTargetModal')?.addEventListener('click', (e) => {
    if (e.target === $('upgradeTargetModal')) closeUpgradeTargetModal();
  });
  $('upgradeWinModal')?.addEventListener('click', (e) => {
    if (e.target === $('upgradeWinModal')) closeUpgradeWinModal();
  });

  document.querySelectorAll('.upgrade-chip-filter').forEach(btn => {
    btn.addEventListener('click', () => filterUpgradeTargets(btn.dataset.rarity));
  });
}

// ─────────────────────────────────────────────────────────────
// TOURNAMENTS LOGIC
// ─────────────────────────────────────────────────────────────

state.tournaments = [];
state.selectedTournamentId = null;
state.adminTournaments = [];

function formatTimeRemaining(endIso) {
  if (!endIso) return 'Бессрочный';
  const end = new Date(endIso).getTime();
  const now = Date.now();
  const diff = end - now;
  if (diff <= 0) return 'Завершён';
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  if (days > 0) return `${days} д. ${hours} ч.`;
  if (hours > 0) return `${hours} ч. ${mins} мин.`;
  return `${mins} мин.`;
}

function formatStars(n) {
  if (n == null) return '0';
  return Number(n).toLocaleString('ru-RU');
}

async function loadTournaments() {
  const container = $('tournamentDetailContainer');
  if (container) container.innerHTML = '<div class="empty-state">Загрузка данных турниров...</div>';
  // Hide the filter bar — we now use cards instead
  const bar = $('tournamentsFilterBar');
  if (bar) bar.style.display = 'none';

  try {
    const data = await api('/api/tournaments');
    const list = data?.tournaments || [];
    state.tournaments = list;

    if (!list.length) {
      if (container) container.innerHTML = '<div class="empty-state">Пока нет созданных турниров. Следите за анонсами!</div>';
      return;
    }

    // Render a compact card for each tournament
    if (container) {
      container.innerHTML = list.map(t => {
        const statusBadge = t.status === 'active' ? '🟢 Идёт' : (t.status === 'upcoming' ? '🟡 Скоро' : '⚪ Завершён');
        const timerLabel = formatTimeRemaining(t.end_time);

        // Games list
        let gamesStr = 'Все игры';
        const gameNames = {
          mines: '💣 Мины', crash: '🚀 Краш', roulette: '🎡 Рулетка', coin: '🪙 Монетка',
          cases: '🎁 Кейсы', tower: '🧗 Башня', plinko: '🟢 Плинко', blackjack: '🃏 Блэкджек',
          dice: '🎲 Кости', upgrade: '⚡ Апгрейд',
        };
        if (t.games && t.games.length && !t.games.includes('all')) {
          gamesStr = t.games.map(g => gameNames[g] || g).join(', ');
        }

        // Prizes summary inline
        let prizeLine = '';
        if (t.prizes && t.prizes.length) {
          prizeLine = t.prizes.map(p => {
            const icon = p.place === 1 ? '🥇' : (p.place === 2 ? '🥈' : '🥉');
            if ((p.prize_type || 'stars') === 'nft') {
              return `${icon} ${escapeHtml(p.nft_name || p.nft_model || 'NFT')}`;
            }
            return `${icon} ${formatStars(p.reward)} ⭐`;
          }).join('  ');
        }

        // Mini leaderboard preview (top-3 from API)
        const preview = t.leaderboard_preview || [];
        const miniLbHtml = preview.length ? `
          <div style="margin-top:10px; border-top:1px solid rgba(255,255,255,0.07); padding-top:10px;">
            <div style="font-size:11px; color:var(--muted,#8e9f96); margin-bottom:6px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">📊 Топ игроков</div>
            ${preview.map((e, i) => {
              const medal = i === 0 ? '🥇' : (i === 1 ? '🥈' : '🥉');
              const isMe = state.bootstrap?.user?.id && String(e.user_id) === String(state.bootstrap.user.id);
              return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:13px;${isMe?'color:#22d3ee;':''}">
                <span style="width:20px;text-align:center;flex-shrink:0;">${medal}</span>
                <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(e.display_name)}${isMe ? ' <span style="font-size:10px;background:rgba(34,211,238,0.15);padding:1px 5px;border-radius:8px;margin-left:3px;">Вы</span>' : ''}</span>
                <strong style="font-size:12px;color:#f59e0b;flex-shrink:0;">${e.formatted_score}</strong>
              </div>`;
            }).join('')}
          </div>
        ` : `<div style="margin-top:8px;font-size:12px;color:var(--muted,#8e9f96);text-align:center;padding-top:8px;border-top:1px solid rgba(255,255,255,0.07);">Пока нет участников — будьте первым!</div>`;

        return `
          <article class="cardish panel tourn-list-card" data-tourn-id="${t.id}" onclick="selectTournament('${t.id}')" style="cursor:pointer; margin-bottom:10px; transition:all 0.15s;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <h3 style="margin:0; font-size:15px;">🏆 ${escapeHtml(t.title)}</h3>
              <span class="tourn-status-badge ${t.status}" style="font-size:11px; padding:3px 10px; border-radius:12px;">${statusBadge}</span>
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:12px; font-size:12px; color:var(--muted,#8e9f96); margin-bottom:6px;">
              <span>💰 Фонд: <strong style="color:#f59e0b;">${formatStars(t.prize_pool)} ⭐</strong></span>
              <span>⏳ ${timerLabel}</span>
              <span>👥 ${t.total_participants || 0} участн.</span>
            </div>

            ${t.criteria_summary || t.metric_title ? `<div style="font-size:12px; color:var(--muted,#8e9f96); margin-bottom:4px;">🎯 ${escapeHtml(t.criteria_summary || t.metric_title)}</div>` : ''}
            ${prizeLine ? `<div style="font-size:12px; margin-top:4px;">${prizeLine}</div>` : ''}

            ${miniLbHtml}

            <div style="text-align:center; margin-top:10px; font-size:11px; color:var(--accent,#6366f1);">Нажмите чтобы открыть подробности ▼</div>
          </article>

          <div id="tournDetail_${t.id}" class="tourn-expanded-detail" style="display:none;"></div>
        `;
      }).join('');
    }

  } catch (err) {
    if (container) container.innerHTML = `<div class="empty-state">Ошибка загрузки турниров: ${escapeHtml(err.message)}</div>`;
  }
}

async function selectTournament(tournamentId) {
  // Toggle: if already open, close it
  const detailEl = document.getElementById(`tournDetail_${tournamentId}`);
  if (!detailEl) return;

  if (detailEl.style.display !== 'none' && state.selectedTournamentId === tournamentId) {
    detailEl.style.display = 'none';
    state.selectedTournamentId = null;
    return;
  }

  // Close all other expanded details
  document.querySelectorAll('.tourn-expanded-detail').forEach(el => { el.style.display = 'none'; });
  state.selectedTournamentId = tournamentId;

  detailEl.style.display = 'block';
  detailEl.innerHTML = '<div class="empty-state">Загрузка таблицы лидеров...</div>';

  try {
    const data = await api(`/api/tournaments/${encodeURIComponent(tournamentId)}`);
    if (!data || !data.ok) {
      detailEl.innerHTML = `<div class="empty-state">${escapeHtml(data?.error || 'Не удалось загрузить данные турнира')}</div>`;
      return;
    }
    renderTournamentView(data, detailEl);
  } catch (err) {
    detailEl.innerHTML = `<div class="empty-state">Ошибка: ${escapeHtml(err.message)}</div>`;
  }
}

function renderTournamentView(data, targetEl) {
  const container = targetEl || $('tournamentDetailContainer');
  if (!container) return;

  const t = data.tournament;
  const lb = data.leaderboard || [];
  const my = data.my_rank || null;

  const statusLabel = t.status === 'active' ? '🟢 Идёт сейчас' : (t.status === 'upcoming' ? '🟡 Скоро начнётся' : '⚪ Завершён');
  const timerLabel = formatTimeRemaining(t.end_time);

  let gamesBadgesHtml = '';
  if (t.games && t.games.length && !t.games.includes('all')) {
    const gameNames = {
      mines: '💣 Мины', crash: '🚀 Краш', roulette: '🎡 Рулетка', coin: '🪙 Монетка',
      cases: '🎁 Кейсы', tower: '🧗 Башня', plinko: '🟢 Плинко', blackjack: '🃏 Блэкджек',
      dice: '🎲 Кости', upgrade: '⚡ Апгрейд',
    };
    gamesBadgesHtml = t.games.map(g => `<span class="tourn-game-tag">${gameNames[g] || g}</span>`).join(' ');
  } else if (!t.metric.includes('purchase') && !t.metric.includes('bought')) {
    gamesBadgesHtml = '<span class="tourn-game-tag">Все игры</span>';
  }

  // Prizes summary
  let prizesHtml = '';
  if (t.prizes && t.prizes.length) {
    prizesHtml = t.prizes.map(p => {
      const placeIcon = p.place === 1 ? '🥇' : (p.place === 2 ? '🥈' : (p.place === 3 ? '🥉' : `#${p.place}`));
      const prizeType = p.prize_type || 'stars';
      let rewardHtml;
      if (prizeType === 'nft') {
        const nftImg = p.nft_image ? `<img src="${escapeHtml(p.nft_image)}" style="width:22px;height:22px;border-radius:4px;object-fit:cover;vertical-align:middle;margin-right:4px;" onerror="this.style.display='none'" />` : '';
        rewardHtml = `<strong class="tourn-prize-val">${nftImg}${escapeHtml(p.nft_name || p.nft_model || 'NFT')}</strong>`;
      } else {
        rewardHtml = `<strong class="tourn-prize-val">${p.reward} ⭐</strong>`;
      }
      return `
        <div class="tourn-prize-col">
          <span class="tourn-prize-place">${placeIcon}</span>
          ${rewardHtml}
        </div>
      `;
    }).join('');
  }

  // User position banner
  let myBannerHtml = '';
  if (my && my.rank) {
    let inPrizeHtml = '';
    if (my.prize_type === 'nft' && my.prize_nft_model) {
      const nftImg = my.prize_nft_image ? `<img src="${escapeHtml(my.prize_nft_image)}" style="width:20px;height:20px;border-radius:3px;object-fit:cover;vertical-align:middle;margin-right:4px;" onerror="this.style.display='none'" />` : '';
      inPrizeHtml = `<div class="tourn-my-prize">🎁 Ожидаемый приз: <strong>${nftImg}${escapeHtml(my.prize_nft_name || my.prize_nft_model)}</strong></div>`;
    } else if (my.prize) {
      inPrizeHtml = `<div class="tourn-my-prize">🎁 Ожидаемый приз: <strong>${my.prize} ⭐</strong></div>`;
    }
    myBannerHtml = `
      <article class="cardish panel tourn-my-card">
        <div class="tourn-my-head">
          <div>
            <span class="eyebrow">Ваше участие</span>
            <h3>Ваша позиция в турнире</h3>
          </div>
          <div class="tourn-rank-badge">#${my.rank}</div>
        </div>
        <div class="tourn-my-stats">
          <div class="tourn-stat-item">
            <span class="tourn-stat-label">Ваш результат</span>
            <strong class="tourn-stat-val">${my.formatted_score}</strong>
          </div>
          <div class="tourn-stat-item">
            <span class="tourn-stat-label">Раундов / действий</span>
            <strong class="tourn-stat-val">${my.rounds_count || 1}</strong>
          </div>
        </div>
        ${inPrizeHtml}
      </article>
    `;
  } else {
    const ctaAction = (t.metric.includes('purchase') || t.metric.includes('bought'))
      ? `switchTab('shop')`
      : `switchTab('games')`;
    const ctaText = (t.metric.includes('purchase') || t.metric.includes('bought'))
      ? `⭐ Купить звёзды`
      : `🎮 Играть`;
    myBannerHtml = `
      <article class="cardish panel tourn-my-card empty-card">
        <div class="tourn-my-head">
          <div>
            <span class="eyebrow">Ваше участие</span>
            <h3>Вы ещё не набрали очков</h3>
          </div>
          <button type="button" class="primary small" onclick="${ctaAction}">${ctaText}</button>
        </div>
        <p class="muted-note">Сыграйте в участвующие игры или пополните баланс звёзд, чтобы автоматически попасть в турнирную таблицу лидеров!</p>
      </article>
    `;
  }

  // Leaderboard table rows
  let leaderboardRowsHtml = '';
  if (!lb.length) {
    leaderboardRowsHtml = `<tr><td colspan="4" class="empty-state" style="text-align:center; padding:24px;">Пока нет участников. Будьте первым!</td></tr>`;
  } else {
    leaderboardRowsHtml = lb.map(entry => {
      const isMe = (state.bootstrap?.user?.id && String(entry.user_id) === String(state.bootstrap.user.id));
      let rankIcon = `#${entry.rank}`;
      if (entry.rank === 1) rankIcon = '🥇 1';
      else if (entry.rank === 2) rankIcon = '🥈 2';
      else if (entry.rank === 3) rankIcon = '🥉 3';

      let prizeBadge = '<span class="muted-dash">—</span>';
      if (entry.prize_type === 'nft' && entry.prize_nft_model) {
        const nftImg = entry.prize_nft_image ? `<img src="${escapeHtml(entry.prize_nft_image)}" style="width:16px;height:16px;border-radius:3px;object-fit:cover;vertical-align:middle;margin-right:3px;" onerror="this.style.display='none'" />` : '';
        prizeBadge = `<span class="tourn-table-prize tourn-table-prize-nft" title="${escapeHtml(entry.prize_nft_name || entry.prize_nft_model)}">${nftImg}${escapeHtml(entry.prize_nft_name || entry.prize_nft_model)}</span>`;
      } else if (entry.prize) {
        prizeBadge = `<span class="tourn-table-prize">+${entry.prize} ⭐</span>`;
      }

      return `
        <tr class="tourn-row ${isMe ? 'current-user-row' : ''} ${entry.rank <= 3 ? 'top-three-row' : ''}">
          <td class="tourn-col-rank"><strong>${rankIcon}</strong></td>
          <td class="tourn-col-user">
            <div class="tourn-user-wrap">
              <span class="tourn-user-name">${escapeHtml(entry.display_name)}</span>
              ${isMe ? '<span class="tourn-you-tag">Вы</span>' : ''}
            </div>
          </td>
          <td class="tourn-col-score"><strong>${entry.formatted_score}</strong></td>
          <td class="tourn-col-prize">${prizeBadge}</td>
        </tr>
      `;
    }).join('');
  }

  container.innerHTML = `
    <!-- Таблица лидеров — ПЕРВОЙ -->
    <article class="cardish panel tourn-leaderboard-card">
      <div class="panel-head">
        <div class="panel-title-group">
          <span class="eyebrow">Онлайн рейтинг</span>
          <h2>📊 Таблица лидеров</h2>
        </div>
        <span class="hint">Участников: ${lb.length}</span>
      </div>

      <div class="table-responsive">
        <table class="tourn-table">
          <thead>
            <tr>
              <th style="width:70px;">Место</th>
              <th>Игрок</th>
              <th>Результат</th>
              <th style="width:110px;">Приз</th>
            </tr>
          </thead>
          <tbody>
            ${leaderboardRowsHtml}
          </tbody>
        </table>
      </div>
    </article>

    <!-- Главная карточка турнира — условия и призы -->
    <article class="cardish panel tourn-banner-card">
      <div class="tourn-banner-top">
        <div class="tourn-badge-group">
          <span class="tourn-status-badge ${t.status}">${statusLabel}</span>
          <span class="tourn-time-badge">⏳ До конца: ${timerLabel}</span>
        </div>
        <div class="tourn-pool-badge">
          <span class="pool-label">Фонд:</span>
          <strong>${formatStars(t.prize_pool)} ⭐</strong>
        </div>
      </div>

      <h1 class="tourn-main-title">${escapeHtml(t.title)}</h1>
      ${t.description ? `<p class="tourn-desc">${escapeHtml(t.description)}</p>` : ''}

      <div class="tourn-metrics-summary">
        <div class="tourn-cond-row">
          <span class="cond-icon">🎯</span>
          <div>
            <strong>Условие турнира:</strong>
            <span class="cond-val">${escapeHtml(t.criteria_summary || t.metric_title)}</span>
          </div>
        </div>
      </div>

      ${prizesHtml ? `
      <div class="tourn-prizes-bar">
        ${prizesHtml}
      </div>
      ` : ''}
    </article>

    <!-- Карточка пользователя — внизу -->
    ${myBannerHtml}
  `;
}

// ─────────────────────────────────────────────────────────────
// ADMIN TOURNAMENTS LOGIC
// ─────────────────────────────────────────────────────────────

function initAdminTournGamesGrid() {
  document.querySelectorAll('#adminTournGamesGrid input[type="checkbox"]').forEach(cb => {
    cb.closest('.tourn-game-check-card')?.classList.toggle('checked', cb.checked);
    if (!cb.dataset.bound) {
      cb.dataset.bound = 'true';
      cb.addEventListener('change', () => {
        cb.closest('.tourn-game-check-card')?.classList.toggle('checked', cb.checked);
      });
    }
  });
}

function handleAdminMetricChange() {
  const metric = $('adminTournMetric')?.value || '';
  const gamesWrap = $('adminTournGamesWrap');
  if (!gamesWrap) return;
  if (metric === 'max_single_purchase' || metric === 'total_stars_bought') {
    gamesWrap.style.display = 'none';
  } else {
    gamesWrap.style.display = 'block';
  }
}

function handleAdminPrizePoolChange() {
  const pool = Number($('adminTournPrizePool')?.value || 0);
  if (pool > 0) {
    for (let place = 1; place <= 3; place++) {
      const typeBtn = document.querySelector(`.prize-type-btn.active[data-place="${place}"]`);
      const currentType = typeBtn?.dataset?.type || 'stars';
      if (currentType === 'stars') {
        const pcts = [0.5, 0.3, 0.2];
        const el = $(`adminTournPrize${place}`);
        if (el) el.value = Math.round(pool * pcts[place - 1]);
      }
    }
  }
}

// ── NFT Prize Picker Modal ───────────────────────────────────
let _prizeNftCatalog = null;
let _tournNftModalTargetPlace = 1;
let _tournNftModalRarity = 'all';

async function loadPrizeNftCatalog() {
  if (_prizeNftCatalog && _prizeNftCatalog.length) return _prizeNftCatalog;

  // 1. Try directly from bootstrap payload
  const fromBootstrap = state.bootstrap?.pricing?.nft_catalog;
  if (Array.isArray(fromBootstrap) && fromBootstrap.length) {
    _prizeNftCatalog = fromBootstrap;
    return _prizeNftCatalog;
  }

  // 2. Try static default catalog
  if (typeof DEFAULT_NFT_GIFTS !== 'undefined' && Array.isArray(DEFAULT_NFT_GIFTS) && DEFAULT_NFT_GIFTS.length) {
    _prizeNftCatalog = DEFAULT_NFT_GIFTS;
    return _prizeNftCatalog;
  }

  // 3. Fallback to endpoint
  try {
    const res = await api('/api/admin/tournaments/nft-catalog');
    if (res?.catalog && res.catalog.length) {
      _prizeNftCatalog = res.catalog;
      return _prizeNftCatalog;
    }
  } catch (_) {}

  _prizeNftCatalog = (typeof DEFAULT_NFT_GIFTS !== 'undefined' && DEFAULT_NFT_GIFTS) || [];
  return _prizeNftCatalog;
}

function setPrizeType(place, type) {
  // Update button states
  document.querySelectorAll(`.prize-type-btn[data-place="${place}"]`).forEach(btn => {
    const isActive = btn.dataset.type === type;
    btn.style.background = isActive ? 'var(--accent,#6366f1)' : 'transparent';
    btn.style.color = isActive ? '#fff' : 'var(--hint,#94a3b8)';
    btn.style.borderColor = isActive ? 'var(--accent,#6366f1)' : 'rgba(255,255,255,0.2)';
    if (isActive) btn.classList.add('active');
    else btn.classList.remove('active');
  });

  // Show/hide sections
  const starsWrap = $(`prizeStarsWrap${place}`);
  const nftWrap = $(`prizeNftWrap${place}`);
  if (starsWrap) starsWrap.style.display = type === 'stars' ? '' : 'none';
  if (nftWrap) nftWrap.style.display = type === 'nft' ? '' : 'none';

  if (type === 'nft') {
    // If no NFT selected yet for this place, automatically open modal dialog
    const currentModel = $(`prizeNftModel${place}`)?.value;
    if (!currentModel) {
      openTournamentNftModal(place);
    }
  }
}

async function openTournamentNftModal(place) {
  _tournNftModalTargetPlace = place;
  const modal = $('tournamentNftModal');
  if (!modal) return;

  const subtitle = $('tournNftModalSubtitle');
  if (subtitle) subtitle.textContent = `Приз за ${place} место`;

  const searchInput = $('tournNftModalSearch');
  if (searchInput) searchInput.value = '';

  _tournNftModalRarity = 'all';
  document.querySelectorAll('#tournamentNftModal .upgrade-chip-filter').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.rarity === 'all');
  });

  // SYNC: fill catalog from DEFAULT_NFT_GIFTS immediately (no await needed)
  if (!_prizeNftCatalog || !_prizeNftCatalog.length) {
    if (state.bootstrap?.pricing?.nft_catalog?.length) {
      _prizeNftCatalog = state.bootstrap.pricing.nft_catalog;
    } else if (typeof DEFAULT_NFT_GIFTS !== 'undefined' && DEFAULT_NFT_GIFTS.length) {
      _prizeNftCatalog = DEFAULT_NFT_GIFTS;
    }
  }

  modal.classList.remove('hidden');
  renderTournamentNftModalGrid(); // render immediately with sync data

  // Background: optionally refresh from server (won't block UI)
  loadPrizeNftCatalog().then(() => renderTournamentNftModalGrid()).catch(() => {});
}

function closeTournamentNftModal() {
  const modal = $('tournamentNftModal');
  if (modal) modal.classList.add('hidden');
}

function setTournNftModalRarity(rarity) {
  _tournNftModalRarity = rarity;
  document.querySelectorAll('#tournamentNftModal .upgrade-chip-filter').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.rarity === rarity);
  });
  renderTournamentNftModalGrid();
}

function filterTournamentNftModal() {
  renderTournamentNftModalGrid();
}

function renderTournamentNftModalGrid() {
  const grid = $('tournNftModalGrid');
  if (!grid) return;

  const catalog = _prizeNftCatalog || [];
  const query = ($('tournNftModalSearch')?.value || '').toLowerCase().trim();
  const rarity = _tournNftModalRarity || 'all';

  let filtered = catalog;
  if (rarity !== 'all') {
    filtered = filtered.filter(item => (item.rarity || 'common').toLowerCase() === rarity.toLowerCase());
  }
  if (query) {
    filtered = filtered.filter(item => (item.name || '').toLowerCase().includes(query) || (item.model || '').toLowerCase().includes(query));
  }

  if (!filtered.length) {
    grid.innerHTML = '<div style="padding:32px; font-size:13px; color:var(--hint,#8e9f96); grid-column:1/-1; text-align:center;">Ничего не найдено</div>';
    return;
  }

  const selectedModel = $(`prizeNftModel${_tournNftModalTargetPlace}`)?.value || '';
  const rarityColor = { common: '#94a3b8', rare: '#22d3ee', epic: '#a78bfa', legendary: '#f59e0b', mythic: '#f43f5e' };

  grid.innerHTML = filtered.map(item => {
    const isSelected = item.model === selectedModel;
    return `
      <div class="upgrade-modal-item ${isSelected ? 'selected' : ''}"
           data-nft-model="${escapeHtml(item.model)}"
           onclick="pickTournamentNftByModel(this.dataset.nftModel)"
           style="cursor:pointer; position:relative; background:rgba(255,255,255,0.04); border:1px solid ${isSelected ? 'var(--accent,#6366f1)' : 'rgba(255,255,255,0.08)'}; border-radius:10px; padding:10px; display:flex; flex-direction:column; align-items:center; text-align:center; transition:all 0.15s;">
        <div style="width:56px; height:56px; margin-bottom:6px; display:flex; align-items:center; justify-content:center;">
          ${item.image ? `<img src="${escapeHtml(item.image)}" style="width:100%; height:100%; object-fit:cover; border-radius:8px;" onerror="this.style.display='none'" />` : '<span style="font-size:32px;">🎁</span>'}
        </div>
        <span style="font-size:10px; font-weight:800; text-transform:uppercase; color:${rarityColor[item.rarity] || '#94a3b8'}; margin-bottom:2px;">${item.rarity || 'common'}</span>
        <strong style="font-size:12px; color:#fff; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(item.name || item.model)}</strong>
        <span style="font-size:11px; color:var(--stars-gold,#f59e0b); font-weight:700; margin-top:2px;">${item.value || 0} ⭐</span>
      </div>
    `;
  }).join('');
}

function pickTournamentNftByModel(model) {
  const item = (_prizeNftCatalog || []).find(c => c.model === model);
  if (!item) return;
  pickTournamentNftItem(item.model, item.name || item.model, item.image || '', item.value || 0);
}

function pickTournamentNftItem(model, name, image, value) {
  const place = _tournNftModalTargetPlace;
  const modelEl = $(`prizeNftModel${place}`);
  if (modelEl) modelEl.value = model;

  const emptyBtn = $(`prizeNftEmpty${place}`);
  if (emptyBtn) emptyBtn.style.display = 'none';

  const rarityColor = { common: '#94a3b8', rare: '#22d3ee', epic: '#a78bfa', legendary: '#f59e0b', mythic: '#f43f5e' };
  const item = (_prizeNftCatalog || []).find(c => c.model === model) || {};
  const rarity = item.rarity || 'common';

  const previewEl = $(`prizeNftPreview${place}`);
  if (previewEl) {
    previewEl.style.display = 'flex';
    previewEl.innerHTML = `
      ${image ? `<img src="${escapeHtml(image)}" style="width:44px; height:44px; border-radius:8px; object-fit:cover; flex-shrink:0;" onerror="this.style.display='none'" />` : '<span style="font-size:28px;">🎁</span>'}
      <div style="flex:1; min-width:0;">
        <div style="font-size:11px; color:#22c55e; font-weight:700;">✓ Выбран приз:</div>
        <div style="font-size:13px; font-weight:700; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(name)}</div>
        <div style="font-size:11px; color:${rarityColor[rarity]}; font-weight:600;">${rarity} · ${value} ⭐</div>
      </div>
      <div style="display:flex; flex-direction:column; gap:4px; margin-left:auto;">
        <button type="button" class="ghost tiny" onclick="openTournamentNftModal(${place})" style="padding:4px 8px; font-size:11px;">Сменить</button>
        <button type="button" class="ghost tiny danger-btn" onclick="clearPrizeNft(${place})" style="padding:4px 8px; font-size:11px; color:var(--bad,#ef4444);">✕</button>
      </div>
    `;
  }

  closeTournamentNftModal();
}

function clearPrizeNft(place) {
  const modelEl = $(`prizeNftModel${place}`);
  if (modelEl) modelEl.value = '';

  const emptyBtn = $(`prizeNftEmpty${place}`);
  if (emptyBtn) emptyBtn.style.display = 'flex';

  const previewEl = $(`prizeNftPreview${place}`);
  if (previewEl) { previewEl.style.display = 'none'; previewEl.innerHTML = ''; }
}

async function loadAdminTournaments() {
  const listEl = $('adminTournamentsList');
  if (listEl) listEl.innerHTML = '<div class="empty-state">Загрузка турниров...</div>';

  try {
    const data = await api('/api/admin/tournaments');
    const tournaments = data?.tournaments || [];
    state.adminTournaments = tournaments;

    if (!tournaments.length) {
      if (listEl) listEl.innerHTML = '<div class="empty-state">Пока нет созданных турниров. Создайте первый турнир выше.</div>';
      return;
    }

    if (listEl) {
      listEl.innerHTML = tournaments.map(t => {
        const statusBadge = t.status === 'active' ? '🟢 Активен' : (t.status === 'upcoming' ? '🟡 Скоро' : '⚪ Завершён');
        const endStr = t.end_time ? new Date(t.end_time).toLocaleString('ru-RU') : 'Бессрочный';

        return `
          <div class="cardish stack-card tourn-admin-card" style="padding:14px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
              <div>
                <strong style="font-size:15px; display:block;">${escapeHtml(t.title)}</strong>
                <span style="font-size:12px; color:var(--muted,#8e9f96);">${escapeHtml(t.criteria_summary || t.metric_title)}</span>
              </div>
              <span class="tourn-status-badge ${t.status}" style="font-size:11px; padding:3px 8px; border-radius:12px;">${statusBadge}</span>
            </div>

            <div style="display:flex; gap:16px; font-size:12px; color:var(--muted,#8e9f96); margin-bottom:10px;">
              <span>🎁 Фонд: <strong>${formatStars(t.prize_pool)} ⭐</strong></span>
              <span>👥 Участников: <strong>${t.total_participants || 0}</strong></span>
              <span>⏳ До: <strong>${endStr}</strong></span>
            </div>

            <div class="actions" style="display:flex; gap:6px; flex-wrap:wrap;">
              ${t.status === 'active' ? `
                <button type="button" class="ghost small" onclick="adminEndTournament('${t.id}')">Завершить</button>
              ` : ''}
              ${!t.prizes_distributed ? `
                <button type="button" class="primary small" onclick="adminDistributeTournamentPrizes('${t.id}')">🎁 Выдать призы</button>
              ` : '<span style="font-size:11px; color:#22c55e; align-self:center;">✅ Призы выданы</span>'}
              <button type="button" class="ghost danger-btn small" onclick="adminDeleteTournament('${t.id}')">Удалить</button>
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    if (listEl) listEl.innerHTML = `<div class="empty-state">Ошибка: ${escapeHtml(err.message)}</div>`;
  }
}

async function adminCreateTournament() {
  const title = $('adminTournTitle')?.value.trim();
  if (!title) {
    toast('Введите название турнира', 'error');
    return;
  }
  const desc = $('adminTournDesc')?.value.trim() || '';
  const metric = $('adminTournMetric')?.value || 'max_single_win';

  const games = [];
  const isPurchaseMetric = (metric === 'max_single_purchase' || metric === 'total_stars_bought');
  if (!isPurchaseMetric) {
    ['Mines', 'Crash', 'Roulette', 'Coin', 'Cases', 'Tower', 'Plinko', 'Blackjack', 'Dice', 'Upgrade'].forEach(name => {
      const el = $(`adminTournGame${name}`);
      if (el && el.checked) games.push(el.value);
    });
  }

  const startTime = $('adminTournStartTime')?.value || null;
  const endTime = $('adminTournEndTime')?.value || null;
  const prizePool = Number($('adminTournPrizePool')?.value || 0);

  const prizes = [];
  for (let place = 1; place <= 3; place++) {
    const typeBtn = document.querySelector(`.prize-type-btn.active[data-place="${place}"]`);
    const prizeType = typeBtn?.dataset?.type || 'stars';

    if (prizeType === 'nft') {
      const nftModel = $(`prizeNftModel${place}`)?.value?.trim();
      if (!nftModel) {
        toast(`Выберите NFT подарок для ${place} места`, 'error');
        return;
      }
      const catalogItem = (_prizeNftCatalog || []).find(c => c.model === nftModel) || {};
      prizes.push({
        place,
        prize_type: 'nft',
        nft_model: nftModel,
        nft_name: catalogItem.name || nftModel,
        nft_image: catalogItem.image || '',
        nft_value: catalogItem.value || 0,
      });
    } else {
      const starsAmount = Number($(`adminTournPrize${place}`)?.value || 0);
      if (starsAmount > 0) {
        prizes.push({ place, prize_type: 'stars', reward: starsAmount });
      }
    }
  }

  const minThreshold = Number($('adminTournMinThreshold')?.value || 0);

  try {
    const res = await api('/api/admin/tournaments/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        init_data: state.initData,
        title,
        description: desc,
        metric,
        games,
        start_time: startTime,
        end_time: endTime,
        prize_pool: prizePool,
        prizes,
        min_threshold: minThreshold,
      }),
    });

    if (res?.ok) {
      toast('🏆 Турнир успешно создан!');
      $('adminTournTitle').value = '';
      $('adminTournDesc').value = '';
      await loadAdminTournaments();
      await loadTournaments();
    } else {
      toast(res?.detail || res?.error || 'Ошибка при создании турнира', 'error');
    }
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function adminEndTournament(tournId) {
  if (!confirm('Завершить турнир досрочно?')) return;
  try {
    const res = await api('/api/admin/tournaments/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, tournament_id: tournId }),
    });
    if (res?.ok) {
      toast('Турнир завершён');
      await loadAdminTournaments();
      await loadTournaments();
    }
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function adminDistributeTournamentPrizes(tournId) {
  if (!confirm('Начислить призы победителям турнира на их баланс Stars?')) return;
  try {
    const res = await api('/api/admin/tournaments/distribute-prizes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, tournament_id: tournId }),
    });
    if (res?.ok) {
      toast(`Призы начислены (${res.distributed_count} победителей)`);
      await loadAdminTournaments();
      await loadTournaments();
    }
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function adminDeleteTournament(tournId) {
  if (!confirm('Удалить этот турнир?')) return;
  try {
    const res = await api('/api/admin/tournaments/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: state.initData, tournament_id: tournId }),
    });
    if (res?.ok) {
      toast('Турнир удалён');
      await loadAdminTournaments();
      await loadTournaments();
    }
  } catch (err) {
    toast(err.message, 'error');
  }
}

// Global window exposure for inline onclicks and external callers
window.loadTournaments = loadTournaments;
window.selectTournament = selectTournament;
window.handleAdminMetricChange = handleAdminMetricChange;
window.handleAdminPrizePoolChange = handleAdminPrizePoolChange;
window.loadAdminTournaments = loadAdminTournaments;
window.adminCreateTournament = adminCreateTournament;
window.adminEndTournament = adminEndTournament;
window.adminDistributeTournamentPrizes = adminDistributeTournamentPrizes;
window.adminDeleteTournament = adminDeleteTournament;
window.switchShopSubtab = switchShopSubtab;
window.setNftShopRarity = setNftShopRarity;
window.onNftShopFilterChange = onNftShopFilterChange;
window.buyNftShopGift = buyNftShopGift;
window.renderNftShop = renderNftShop;
window.filterAdminNftPrices = filterAdminNftPrices;
window.filterAdminNftImages = filterAdminNftImages;
window.adminAddNewNftGift = adminAddNewNftGift;

window.openUpgradeInventoryModal = openUpgradeInventoryModal;
window.closeUpgradeInventoryModal = closeUpgradeInventoryModal;
window.selectUpgradeInventoryGift = selectUpgradeInventoryGift;
window.openUpgradeTargetModal = openUpgradeTargetModal;
window.closeUpgradeTargetModal = closeUpgradeTargetModal;
window.filterUpgradeTargets = filterUpgradeTargets;
window.selectUpgradeTarget = selectUpgradeTarget;
window.setUpgradeBetMode = setUpgradeBetMode;
window.onUpgradeStarsInput = onUpgradeStarsInput;
window.setUpgradeStarsAmount = setUpgradeStarsAmount;
window.setUpgradeStarsMax = setUpgradeStarsMax;
window.clearUpgradeBet = clearUpgradeBet;
window.clearUpgradeTarget = clearUpgradeTarget;
window.playUpgrade = playUpgrade;
window.startUpgradeWithItem = startUpgradeWithItem;
window.closeUpgradeWinModal = closeUpgradeWinModal;
window.initUpgradeUI = initUpgradeUI;

window.copyReferralLink = copyReferralLink;
window.shareReferralLink = shareReferralLink;
window.renderReferrals = renderReferrals;
window.adminResetTrackedUserAllGames = adminResetTrackedUserAllGames;

// ==============================
// УПРАВЛЕНИЕ СМЕНАМИ В МИНИ-АППКЕ
// ==============================
let adminShiftsCachedState = null;

async function loadAdminShiftsState() {
  const badge = document.getElementById('adminShiftStatusBadge');
  const details = document.getElementById('adminShiftDetailsBox');
  const list = document.getElementById('adminShiftWorkersList');
  if (badge) badge.textContent = 'Обновление...';
  try {
    const q = state.initData ? `?init_data=${encodeURIComponent(state.initData)}` : '';
    const data = await api(`/api/admin/shifts/state${q}`);
    adminShiftsCachedState = data;
    const cur = data.current_shift;
    const m = data.current_metrics || {};

    if (badge) {
      if (cur) {
        badge.textContent = '🟢 Активна';
        badge.style.color = '#4ade80';
      } else {
        badge.textContent = '⚪️ Не открыта';
        badge.style.color = 'var(--hint)';
      }
    }

    if (details) {
      if (!cur) {
        details.innerHTML = `
          <div style="padding: 10px 0; color: var(--hint);">
            <strong>Смена не открыта.</strong><br>
            Сейчас платежи принимаются на стандартные реквизиты бота.<br>
            Нажмите <em>«Взять смену на себя»</em> или выберите сменщика из списка ниже.
          </div>
        `;
      } else {
        const usernameStr = cur.username ? `@${cur.username}` : '—';
        details.innerHTML = `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px;">
            <div>
              <div style="font-size: 11px; color: var(--hint);">Сменщик</div>
              <div style="font-size: 15px; font-weight: 700; color: #fff;">${escapeHtml(cur.worker_name || '—')}</div>
              <div style="font-size: 12px; color: var(--accent);">${escapeHtml(usernameStr)}</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--hint);">Карта Mono</div>
              <div style="font-family: monospace; font-size: 13px; font-weight: 600;">${escapeHtml(cur.mono_card || '—')}</div>
              <div style="font-size: 11px; color: var(--hint); margin-top: 2px;">TON: <span style="font-family: monospace;">${escapeHtml(cur.ton_address ? cur.ton_address.slice(0, 10) + '...' + cur.ton_address.slice(-6) : '—')}</span></div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--hint);">Начало смены</div>
              <div style="font-size: 13px; font-weight: 600;">${escapeHtml(cur.started_at || '—')}</div>
              <div style="font-size: 11px; color: var(--hint);">Кем открыта: ${escapeHtml(cur.started_by || 'Admin')}</div>
            </div>
          </div>
          <div style="background: rgba(255,255,255,0.04); border-radius: 8px; padding: 10px; display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; font-size: 12px;">
            <div><span style="color:var(--hint);">Заказов:</span> <strong>${m.total_orders || 0}</strong></div>
            <div><span style="color:var(--hint);">Подтверждено:</span> <strong style="color:#4ade80;">${m.confirmed_count || 0}</strong></div>
            <div><span style="color:var(--hint);">Выручка UAH:</span> <strong style="color:#fbbf24;">${(m.revenue_uah || 0).toFixed(2)} ₴</strong></div>
            <div><span style="color:var(--hint);">Выручка TON:</span> <strong style="color:#38bdf8;">${(m.revenue_ton || 0).toFixed(4)} TON</strong></div>
            <div><span style="color:var(--hint);">Stars продано:</span> <strong style="color:#fbbf24;">${m.stars_sold || 0} ⭐</strong></div>
          </div>
        `;
      }
    }

    if (list) {
      const workers = data.workers || [];
      if (!workers.length) {
        list.innerHTML = '<div class="empty-state">Список сменщиков пуст</div>';
      } else {
        const curId = cur ? String(cur.worker_id) : null;
        list.innerHTML = workers.map(w => {
          const isCur = String(w.id) === curId;
          const badgeHtml = isCur
            ? '<span style="background: rgba(74,222,128,0.2); color: #4ade80; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">🟢 НА СМЕНЕ</span>'
            : (w.is_active ? '<span style="color:var(--hint); font-size: 11px;">активен</span>' : '<span style="color:#ef4444; font-size: 11px;">отключен</span>');
          const tgStr = w.username ? `@${w.username}` : (w.telegram_id ? `ID: ${w.telegram_id}` : 'без TG');
          return `
            <div class="cardish" style="padding: 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
              <div>
                <div style="font-weight: 600; font-size: 14px;">${escapeHtml(w.name)} ${badgeHtml}</div>
                <div style="font-size: 12px; color: var(--hint); margin-top: 2px;">
                  📱 ${escapeHtml(tgStr)} | 💳 <span style="font-family: monospace;">${escapeHtml(w.mono_card || '—')}</span>
                </div>
                ${w.notes ? `<div style="font-size: 11px; color: var(--hint); font-style: italic;">${escapeHtml(w.notes)}</div>` : ''}
              </div>
              <div>
                ${!isCur ? `<button class="ghost small" onclick="handleAdminShiftStartWorker('${escapeHtml(w.id)}')">Начать смену</button>` : ''}
              </div>
            </div>
          `;
        }).join('');
      }
    }
  } catch (err) {
    console.error('loadAdminShiftsState error:', err);
    if (badge) badge.textContent = 'Ошибка';
    toast(err.message || 'Ошибка загрузки смен', 'error');
  }
}

async function handleAdminShiftTakeSelf() {
  const profile = state.bootstrap?.profile || {};
  const actorName = profile.username ? `@${profile.username}` : (profile.first_name || 'Admin');
  try {
    const res = await api('/api/admin/shifts/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: adminShiftsCachedState?.workers?.[0]?.id || 'worker_1',
        actor_name: actorName,
        init_data: state.initData || 'desktop'
      })
    });
    if (res.ok) {
      toast('Смена успешно активирована!', 'success');
      loadAdminShiftsState();
    }
  } catch (err) {
    toast(err.message || 'Ошибка при взятии смены', 'error');
  }
}

async function handleAdminShiftStartWorker(workerId) {
  const profile = state.bootstrap?.profile || {};
  const actorName = profile.username ? `@${profile.username}` : (profile.first_name || 'Admin');
  try {
    const res = await api('/api/admin/shifts/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: workerId,
        actor_name: actorName,
        init_data: state.initData || 'desktop'
      })
    });
    if (res.ok) {
      toast(`Смена переключена на: ${res.shift?.worker_name || 'сменщика'}!`, 'success');
      loadAdminShiftsState();
    }
  } catch (err) {
    toast(err.message || 'Ошибка при переключении смены', 'error');
  }
}

function openShiftTransferModal() {
  const modal = document.getElementById('shiftTransferModal');
  const container = document.getElementById('shiftTransferWorkersOptions');
  if (!modal || !container) return;
  const workers = adminShiftsCachedState?.workers || [];
  const curId = adminShiftsCachedState?.current_shift?.worker_id;
  const otherWorkers = workers.filter(w => String(w.id) !== String(curId) && w.is_active);

  if (!otherWorkers.length) {
    container.innerHTML = '<div style="color:var(--hint); padding: 10px 0;">Нет других активных сменщиков.</div>';
  } else {
    container.innerHTML = otherWorkers.map(w => `
      <button type="button" class="cardish" style="text-align: left; padding: 10px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); cursor: pointer;" onclick="handleAdminShiftTransfer('${escapeHtml(w.id)}')">
        <div style="font-weight: 600; font-size: 14px; color: #fff;">${escapeHtml(w.name)}</div>
        <div style="font-size: 12px; color: var(--hint); margin-top: 2px;">💳 Mono: ${escapeHtml(w.mono_card || '—')}</div>
      </button>
    `).join('');
  }
  modal.classList.remove('hidden');
}

function closeShiftTransferModal() {
  document.getElementById('shiftTransferModal')?.classList.add('hidden');
}

async function handleAdminShiftTransfer(workerId) {
  closeShiftTransferModal();
  const profile = state.bootstrap?.profile || {};
  const actorName = profile.username ? `@${profile.username}` : (profile.first_name || 'Admin');
  try {
    const res = await api('/api/admin/shifts/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: workerId,
        actor_name: actorName,
        init_data: state.initData || 'desktop'
      })
    });
    if (res.ok) {
      toast(`Смена успешно передана: ${res.shift?.worker_name || 'новому сменщику'}!`, 'success');
      loadAdminShiftsState();
    }
  } catch (err) {
    toast(err.message || 'Ошибка при передаче смены', 'error');
  }
}

async function handleAdminGenerateXReport() {
  const profile = state.bootstrap?.profile || {};
  const actorName = profile.username ? `@${profile.username}` : (profile.first_name || 'Admin');
  try {
    const res = await api('/api/admin/shifts/x-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actor_name: actorName,
        init_data: state.initData || 'desktop'
      })
    });
    if (res.ok && res.report) {
      showReportModal(res.report, false);
      toast('X-отчет успешно сформирован!', 'success');
    }
  } catch (err) {
    toast(err.message || 'Ошибка при снятии X-отчета', 'error');
  }
}

async function handleAdminCloseShift() {
  if (!confirm('Вы действительно хотите завершить текущую смену?\nБудет снят и зафиксирован финальный Z-отчет.')) return;
  const profile = state.bootstrap?.profile || {};
  const actorName = profile.username ? `@${profile.username}` : (profile.first_name || 'Admin');
  try {
    const res = await api('/api/admin/shifts/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actor_name: actorName,
        init_data: state.initData || 'desktop'
      })
    });
    if (res.ok) {
      toast('Смена успешно закрыта!', 'success');
      if (res.z_report) {
        showReportModal(res.z_report, true);
      }
      loadAdminShiftsState();
    }
  } catch (err) {
    toast(err.message || 'Ошибка при закрытии смены', 'error');
  }
}

function showReportModal(report, isClosing) {
  const modal = document.getElementById('xReportModal');
  const title = document.getElementById('xReportModalTitle');
  const content = document.getElementById('xReportContent');
  if (!modal || !content) return;

  if (title) {
    title.textContent = isClosing ? '🧾 Z-ОТЧЕТ (ЗАКРЫТИЕ СМЕНЫ)' : '📑 X-ОТЧЕТ (ПРОМЕЖУТОЧНЫЙ)';
  }

  const m = report.metrics || {};
  const bd = m.breakdown || {};
  const text = [
    `ОТЧЕТ: ${report.report_id || '—'}`,
    `Сменщик: ${report.worker_name || '—'}`,
    `Карта Mono: ${report.mono_card || '—'}`,
    `TON адрес: ${report.ton_address || '—'}`,
    `Период: ${report.period_start || '—'} — ${report.period_end || '—'}`,
    `Снял: ${report.generated_by || 'Admin'}`,
    `--------------------------------------`,
    `ИТОГИ:`,
    `  • Всего заявок: ${m.total_orders || 0}`,
    `  • Подтверждено: ${m.confirmed_count || 0}`,
    `  • Отклонено: ${m.rejected_count || 0}`,
    `  • В обработке: ${m.pending_count || 0}`,
    ``,
    `ФИНАНСЫ:`,
    `  • Выручка (UAH): ${(m.revenue_uah || 0).toFixed(2)} ₴`,
    `  • Выручка (TON): ${(m.revenue_ton || 0).toFixed(4)} TON`,
    `  • Выплаты (UAH): ${(m.payouts_uah || 0).toFixed(2)} ₴`,
    `  • Выплаты (TON): ${(m.payouts_ton || 0).toFixed(4)} TON`,
    `  • Чистый итог (UAH): ${(m.net_uah || 0).toFixed(2)} ₴`,
    `  • Чистый итог (TON): ${(m.net_ton || 0).toFixed(4)} TON`,
    ``,
    `ПРОДАЖИ:`,
    `  • Stars выдано: ${m.stars_sold || 0} ⭐`,
    `  • Заказов Stars: ${bd.stars_orders || 0}`,
    `  • Telegram Premium: ${bd.premium_orders || 0}`,
    `  • Пополнений TON: ${bd.ton_topup_orders || 0}`,
  ].join('\n');

  content.textContent = text;
  modal.classList.remove('hidden');
}

function closeXReportModal() {
  document.getElementById('xReportModal')?.classList.add('hidden');
}

window.loadAdminShiftsState = loadAdminShiftsState;
window.handleAdminShiftTakeSelf = handleAdminShiftTakeSelf;
window.handleAdminShiftStartWorker = handleAdminShiftStartWorker;
window.openShiftTransferModal = openShiftTransferModal;
window.closeShiftTransferModal = closeShiftTransferModal;
window.handleAdminShiftTransfer = handleAdminShiftTransfer;
window.handleAdminGenerateXReport = handleAdminGenerateXReport;
window.handleAdminCloseShift = handleAdminCloseShift;
window.closeXReportModal = closeXReportModal;

if (!enforceTelegramClient()) {
  console.warn('Доступ заблокирован: Mini App открыт вне Telegram.');
} else {
  renderCaseConfigurations();
  renderInventory();
  renderNftShop();
  renderReferrals();

  bind();
  initMobileScrollSpy();
  loadBootstrap().catch(err => toast(err.message, 'error'));
}
