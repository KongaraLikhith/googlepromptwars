import { validBrief, validPlan } from './plan-utils.js';

const STORAGE_KEY = 'gatherly.plan.v1';
const MAX_SAVED_CHARACTERS = 100000;

/** Storage can be denied or full; the planner remains usable in memory. */
export function createPlanStore(getStorage = () => globalThis.localStorage) {
  return {
    load() {
      try {
        const serialized = getStorage().getItem(STORAGE_KEY);
        if (!serialized || serialized.length > MAX_SAVED_CHARACTERS) return null;
        const saved = JSON.parse(serialized);
        if (saved?.version !== 1 || !validPlan(saved.plan) || !validBrief(saved.brief, saved.plan)) return null;
        const vendorIds = new Set(saved.plan.vendors.map(item => item.id));
        saved.completed = Array.isArray(saved.completed)
          ? [...new Set(saved.completed.filter(id => vendorIds.has(id)))] : [];
        return saved;
      } catch {
        return null;
      }
    },
    save({ brief, plan, completed }) {
      try {
        const serialized = JSON.stringify({ version: 1, brief, plan, completed: [...completed] });
        if (serialized.length > MAX_SAVED_CHARACTERS) return false;
        getStorage().setItem(STORAGE_KEY, serialized);
        return true;
      } catch {
        return false;
      }
    },
    clear() {
      try {
        getStorage().removeItem(STORAGE_KEY);
        return true;
      } catch {
        return false;
      }
    },
  };
}
