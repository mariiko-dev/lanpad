/**
 * Temporary minimal shape of the user settings.
 *
 * Task 7 owns the full settings model and will widen this interface to
 * cover every preference. Until then only the fields the trackpad needs
 * live here; this is a deliberate stopgap, not a forgotten stub.
 */
export interface Settings {
  sensitivity: number;
  naturalScrolling: boolean;
}
