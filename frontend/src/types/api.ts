export type MeResponse = {
  id: string;
  keycloak_sub: string;
  username: string | null;
  email: string | null;
  display_name: string | null;
  roles: string[];
};
