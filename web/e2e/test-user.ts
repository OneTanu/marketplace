/** Verified student created by backend/scripts/e2e_server.sh in the throwaway E2E database. */
export const TEST_USER = {
  email: "e2e-student@umd.edu",
  // Made from the email by create_verified_user.
  username: "e2e_student",
  password: "e2e-only-password-not-secret",
};

/** A second verified student at the same school, for looking at TEST_USER's listings. */
export const TEST_BUYER = {
  email: "e2e-buyer@umd.edu",
  username: "e2e_buyer",
  password: TEST_USER.password,
};

export type TestUser = typeof TEST_USER;
