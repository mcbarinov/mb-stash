/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** Data Directory - Path to mb-stash data directory */
  "dataDir": string,
  /** mb-stash CLI Path - Path to mb-stash CLI binary (for daemon startup) */
  "mbStashPath": string
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `stash` command */
  export type Stash = ExtensionPreferences & {}
  /** Preferences accessible in the `lock-stash` command */
  export type LockStash = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `stash` command */
  export type Stash = {}
  /** Arguments passed to the `lock-stash` command */
  export type LockStash = {}
}

