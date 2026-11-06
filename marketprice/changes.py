"""Compare recorded per-unit results without inventing sales or missing costs."""

from collections import Counter

from .precision import financial
from .validation import number

FIELDS = ('revenue', 'cogs', 'fixed_expenses', 'commission', 'payment',
          'other_variable', 'fee_tax', 'fee_tax_credit', 'transaction_tax', 'profit')


def identity(row):
    return tuple(str(row.get(field) or '').strip() for field in ('marketplace', 'sku', 'currency'))


@financial
def compare_snapshots(previous, current):
    """Return source-linked differences; ambiguous identities are never paired."""
    indexes = []
    errors = []
    ambiguous: set[tuple[str, ...]] = set()
    for side, rows in [('previous', previous), ('current', current)]:
        counts = Counter(identity(row) for row in rows)
        ambiguous.update(key for key, count in counts.items() if count > 1)
        index = {}
        for row in rows:
            key = identity(row)
            if not all(key) or counts[key] != 1:
                errors.append({'snapshot': side, 'source_row': row.get('row'),
                               'sku': row.get('sku'), 'error': 'Missing or duplicate marketplace/SKU/currency'})
                continue
            index[key] = row
        indexes.append(index)
    before, after = indexes
    changes = []
    # A duplicate on either side invalidates pairing on both sides.
    for key in sorted(before.keys() | after.keys()):
        if key in ambiguous:
            continue
        old, new = before.get(key), after.get(key)
        record = dict(zip(('marketplace', 'sku', 'currency'), key))
        record.update(previous_row=old.get('row') if old else None,
                      current_row=new.get('row') if new else None, decision_ready=False)
        if old is None or new is None:
            changes.append({**record, 'review': 'ADDED' if old is None else 'REMOVED'})
            continue
        if any(r.get('status') != 'VALID' for r in (old, new)):
            changes.append({**record, 'review': 'FIX_PRODUCT'})
            continue
        try:
            delta = {field: number(new[field]) - number(old[field]) for field in FIELDS}
        except (KeyError, ValueError):
            changes.append({**record, 'review': 'INCOMPLETE_LEDGER'})
            continue
        confirmed = all(r.get('cost_confidence') == 'CONFIRMED_INPUTS' for r in (old, new))
        changes.append({**record, 'review': 'REVIEW_CHANGE' if confirmed else 'CONFIRM_COSTS',
                        **{field + '_change': value for field, value in delta.items()}})
    # Ranking is per currency and per unit, never an estimate of total business loss.
    changes.sort(key=lambda r: (r['currency'], r.get('profit_change', 0), r['marketplace'], r['sku']))
    return {'Changes': changes, 'Match_Errors': errors}
