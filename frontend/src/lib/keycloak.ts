import Keycloak from "keycloak-js";

let instance: Keycloak | null = null;

function required(value: string | undefined, name: string): string {
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}

// Created lazily so it only ever runs in the browser, never during server rendering.
export function getKeycloak(): Keycloak {
  if (!instance) {
    instance = new Keycloak({
      url: required(process.env.NEXT_PUBLIC_KEYCLOAK_URL, "NEXT_PUBLIC_KEYCLOAK_URL"),
      realm: required(process.env.NEXT_PUBLIC_KEYCLOAK_REALM, "NEXT_PUBLIC_KEYCLOAK_REALM"),
      clientId: required(
        process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID,
        "NEXT_PUBLIC_KEYCLOAK_CLIENT_ID",
      ),
    });
  }
  return instance;
}