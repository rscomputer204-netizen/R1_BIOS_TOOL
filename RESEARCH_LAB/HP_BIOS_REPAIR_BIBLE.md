# 📖 HP BIOS Forensic Repair & Unlock Bible
*Generated on 2026-09-27 22:39:09 by R1 BIOS Research Lab*

এই ডকুমেন্টে HP ল্যাপটপের বাস্তব ডাম্প (Real Dumps) বিশ্লেষণ করে পাসওয়ার্ড আনলক, Error 34 ফিক্স এবং MPM ক্লিয়ারিং-এর সার্বজনীন নিয়ম ও অফসেট লিপিবদ্ধ করা হয়েছে।

---

## 📑 সূচিপত্র
1. [HP পাসওয়ার্ড আনলক নিয়মাবলী (G5, G6, G7, G8, G9, G10)](#1-hp-পাসওয়ার্ড-আনলক-নিয়মাবলী)
2. [Error 34 / Endpoint Security Controller সমাধান](#2-error-34--endpoint-security-controller-সমাধান)
3. [Manufacturing Programming Mode (MPM) আনলক স্টেট ক্লিয়ার](#3-manufacturing-programming-mode-mpm-আনলক-স্টেট-ক্লিয়ার)
4. [পরীক্ষিত বাস্তব কেস হিস্ট্রি ও ডাটাবেস](#4-পরীক্ষিত-বাস্তব-কেস-হিস্ট্রি)

---

## 1. HP পাসওয়ার্ড আনলক নিয়মাবলী

### 🎯 মূল আর্কিটেকচার:
- **সিঙ্গেল চিপ (Single SPI):** সাধারণত ৩২ MB চিপ থাকে। পাসওয়ার্ড `0x00037000` অফসেটে `NvramActiveRegn` ব্লকে থাকে।
- **ডুয়াল চিপ (Dual SPI):** ১৬ MB (EC) + ৩২ MB (Main)। **পাসওয়ার্ড কখনো ৩২ MB মেইন বায়োসে থাকে না!** পাসওয়ার্ড থাকে **১৬ MB EC চিপের `0x00037000` অফসেটে**।

### ⚡ আনলক অ্যাকশন (Rule):
1. চিপের **`0x00037000`** হতে **`0x00037FFF`** (৪ KB সেক্টর) অংশটি পরীক্ষা করুন।
2. যদি এতে `NvramActiveRegn`, `H_AuthVar`, `H_Hmacslt` থাকে, তবে এই ৪ KB অংশকে সম্পূর্ণ **`0xFF`** করে দিন।
3. **সাবধানতা:** `0x00038000` (`L_MpmPolcy`) এবং `0x00064000` (`PKheaders`) স্পর্শ করবেন না। এতে DMI, Serial Number ও Windows Key শতভাগ অক্ষত থাকে।

---

## 2. Error 34 / Endpoint Security Controller সমাধান

### 🔍 সমস্যার লক্ষণ:
ল্যাপটপ অন করলে ৩ মিনিট ফ্যান ফুল স্পিডে ঘুরে বা স্ক্রিনে ওয়ার্নিং মেসেজ দেয়:  
`HP Sure Start detected an unauthorized change / Endpoint Security Controller 34 error`

### 💡 মূল কারণ ও সমাধান:
- বায়োস বিল্ড বা ক্লিন করার সময় মেইন বায়োসের **`0x018F4000` হতে `0x018F7FFF`** (বা ১০৩০ G5 এ `0x01AFC000`) অংশে থাকা **১৬ KB Secure Platform Certificate / Volume** মুছে গিয়ে `0xFF` হয়ে যায়।
- **সমাধান রুল:** অফিসিয়াল ক্লিন ডাম্প থেকে এই ১৬ KB অংশ কপি করে ক্ষতিগ্রস্ত ফাইলের `0x018F4000` এ পেস্ট করলেই Error 34 চিরতরে দূর হয়ে যায়।

---

## 3. Manufacturing Programming Mode (MPM) আনলক স্টেট ক্লিয়ার

### 🔍 সমস্যার লক্ষণ:
প্রতিবার অন করার সময় লাল অক্ষরে ওয়ার্নিং আসে: *"Manufacturing Programming Mode is in Unlock State"*।

### 💡 সমাধান রুল:
UEFI NVRAM Variable স্টোরে `UserCred` ভেরিয়েবলের স্টেট ফ্ল্যাগ **`0x3F`** (`VAR_ADDED`) থেকে কমিয়ে **`0x3C`** (`VAR_DELETED`) করে দিলে সিস্টেম MPM মোড লক করে দেয় এবং ওয়ার্নিং চলে যায়।

---

## 4. পরীক্ষিত বাস্তব কেস হিস্ট্রি

### 📌 কেস: ZBook 14u G6 / 15u G6 (HP G6 (Whiskey Lake))
- **ক্যাটাগরি:** `PASSWORD_UNLOCK`
- **মাদারবোর্ড:** `6050A3022501-MB-A01`
- **টার্গেট চিপ:** `EC_BIOS_16MB`
- **মোট পরিবর্তিত বাইট:** 2,214 বাইট (1 টি ব্লকে)
- **বর্ণনা:** EC Password removal via 0x00037000 sector wipe

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x00037000 | 0x000378A7 | 2,216 B | **ERASE_ALL_FF** | `NvramActiveRegn, H_AuthVar, H_Hmacslt, H_SsStts` |

---

### 📌 কেস: ProBook 440 G8 (HP G8 (Tiger Lake 11th Gen))
- **ক্যাটাগরি:** `PASSWORD_UNLOCK`
- **মাদারবোর্ড:** `DAX8QAMB8D0 REV D`
- **টার্গেট চিপ:** `EC_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 2,119 বাইট (1 টি ব্লকে)
- **বর্ণনা:** G8 32MB EC Password removal via 0x00037000 sector wipe

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x00037000 | 0x00037849 | 2,122 B | **ERASE_ALL_FF** | `NvramActiveRegn, H_AuthVar, H_Hmacslt, H_SsStts` |

---

### 📌 কেস: ProBook 450 G8 (HP G8 (Tiger Lake 11th Gen))
- **ক্যাটাগরি:** `PASSWORD_UNLOCK`
- **মাদারবোর্ড:** `Intel 11th Gen`
- **টার্গেট চিপ:** `MAIN_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 3,382 বাইট (2 টি ব্লকে)
- **বর্ণনা:** ProBook 450 G8 password removal via 0x00037000 & 0x00038000 wipe

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x00037000 | 0x00037B93 | 2,964 B | **ERASE_ALL_FF** | `NvramActiveRegn, H_AuthVar, H_Hmacslt, H_SsStts` |
| 0x00038000 | 0x000381A9 | 426 B | **ERASE_ALL_FF** | `NvramActiveRegn, L_MpmPolcy` |

---

### 📌 কেস: EliteBook x360 1040 G6 (HP G6 (Whiskey Lake))
- **ক্যাটাগরি:** `ERROR_34_FIX`
- **মাদারবোর্ড:** `6050A3037501-MB-A01`
- **টার্গেট চিপ:** `MAIN_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 16,017 বাইট (1 টি ব্লকে)
- **বর্ণনা:** Error 34 fix: restored missing 16KB Secure Platform Certificate block at 0x018F4000

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x018F4000 | 0x018F7F2A | 16,171 B | **RESTORED_FROM_FF** | `_FVH` |

---

### 📌 কেস: ZBook G6 Crescent (HP G6 (Whiskey Lake))
- **ক্যাটাগরি:** `ERROR_34_FIX`
- **মাদারবোর্ড:** `6050A3022501-MB-A01`
- **টার্গেট চিপ:** `MAIN_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 15,298 বাইট (1 টি ব্লকে)
- **বর্ণনা:** Error 34 fix: restored missing 16KB volume at 0x018F4000

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x018F4000 | 0x018F7C5A | 15,451 B | **RESTORED_FROM_FF** | `_FVH` |

---

### 📌 কেস: EliteBook x360 1030 G5 (HP G5 (Kaby Lake R))
- **ক্যাটাগরি:** `ERROR_34_FIX`
- **মাদারবোর্ড:** `6050A2930901-MB-A01`
- **টার্গেট চিপ:** `MAIN_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 9,139 বাইট (1 টি ব্লকে)
- **বর্ণনা:** Error 34 fix: restored missing Secure Boot Variable Signer block at 0x01AFC160

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x01AFC160 | 0x01AFE572 | 9,235 B | **RESTORED_FROM_FF** | `None` |

---

### 📌 কেস: ZBook Firefly 14 G7 (HP G7 (Comet Lake 10th Gen))
- **ক্যাটাগরি:** `MPM_CLEAR`
- **মাদারবোর্ড:** `6050A3136201-MB-A01`
- **টার্গেট চিপ:** `MAIN_BIOS_32MB`
- **মোট পরিবর্তিত বাইট:** 14 বাইট (12 টি ব্লকে)
- **বর্ণনা:** MPM Mode clear: flipped UEFI UserCred state flag from 0x3F to 0x3C and payload 0x01 to 0x00

| ব্লক | শুরুর অফসেট | শেষের অফসেট | সাইজ | প্যাটার্ন | সিগনেচার |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0x018EC556 | 0x018EC556 | 1 B | **BYTE_PATCH** | `None` |
| 0x018F0596 | 0x018F0596 | 1 B | **BYTE_PATCH** | `None` |
| 0x018F061A | 0x018F061A | 1 B | **BYTE_PATCH** | `None` |
| 0x018F170A | 0x018F170A | 1 B | **BYTE_PATCH** | `None` |
| 0x018F1A5E | 0x018F1A5E | 1 B | **BYTE_PATCH** | `None` |
| 0x018F1C12 | 0x018F1C12 | 1 B | **BYTE_PATCH** | `None` |
| 0x018F1E5E | 0x018F1E5E | 1 B | **BYTE_PATCH** | `None` |
| 0x018F1F56 | 0x018F1F56 | 1 B | **BYTE_PATCH** | `None` |
| 0x018F21A1 | 0x018F21A4 | 4 B | **BYTE_PATCH** | `None` |
| 0x018F70A2 | 0x018F70A2 | 1 B | **BYTE_PATCH** | `None` |
| 0x018F70EE | 0x018F70EE | 1 B | **ZERO_ALL_00** | `None` |
| 0x018FC372 | 0x018FC372 | 1 B | **BYTE_PATCH** | `None` |

---
