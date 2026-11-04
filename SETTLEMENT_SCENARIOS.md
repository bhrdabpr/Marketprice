# What if settlement is delayed? / اثر تأخیر تسویه

An optional pricing sensitivity test for sellers evaluating delayed cash receipts. It does not forecast payouts, read seller accounts, or assume that a customer's instalment schedule equals the seller's settlement schedule.

## Use
1. Calculate and correct your catalog as usual.
2. Open Campaigns → What if settlement is delayed?
3. Enter **additional** delay days beyond financing already included and a seller-chosen annual capital-cost percentage. Zero defaults make no claim about actual terms.
4. Confirm that the scenario does not duplicate existing financing costs.
5. Compare current-sale and campaign rows. Download the JSON evidence with UTC review time, assumptions and source calculation snapshot.

## Model
Capital base = purchase cost minus modeled input tax credit (net acquisition cost).
Additional cost = capital base × annual rate × extra days /365.
Scenario contribution = original contribution − additional cost.

Synthetic example, in IRR: net cost1000, current price1200, no other expenses. Current contribution200. A10% discount gives price1080/contribution80. Annual rate36.5% and30additional days cost30, leaving170/current and50/campaign. At200days, current contribution is zero and campaign contribution is−120. The same proportional arithmetic works in TOMAN without changing rates/days. Display conversion never modifies source amounts.

This is simple ACT/365 sensitivity, not an APR disclosure, compounding, present-value valuation, accounting adjustment or contract repayment model. It assumes the same net acquisition capital remains funded for all entered additional days. It excludes inventory holding time before sale, tax-credit receipt timing and financing other costs. Partial/early repayments and additional campaign spending are not modeled. Inputs are seller assumptions, not verified market facts.

Original results and approvals are unchanged. All scenario rows have decision_ready=false. Positive contribution does not establish target-margin compliance or higher total profit. Invalid rows remain visible, and uncertain costs produce CONFIRM_COSTS. Source campaign safety is retained separately so a positive scenario cannot hide an already unsafe campaign.

## فارسی

این بخش برای مقایسه اثر هزینه اضافی سرمایه است؛ زمان تسویه دیجی‌کالا، اسنپ یا هر قرارداد دیگری را حدس نمی‌زند. فقط روزها و هزینه‌ای را وارد کنید که قبلاً در محاسبه تأمین مالی لحاظ نشده است. مبنا بهای خرید پس از اعتبار مالیاتی مدل است، نه کل وجه نقد پرداختی. اگر زمان دریافت اعتبار مالیاتی، بازپرداخت‌های مرحله‌ای یا هزینه تأمین مالی سایر مخارج مهم است، این مدل کافی نیست. سود مثبت به معنی رسیدن به حاشیه هدف یا تأیید کمپین نیست.
