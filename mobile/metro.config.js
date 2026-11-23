const path = require('path');
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

const projectRoot = __dirname;
// mobile/src/api-client re-exports web/src/api-client/client.ts (see its
// docstring) — Metro needs to know that directory exists outside its
// default project root to watch/resolve it.
const sharedApiClientDir = path.resolve(projectRoot, '..', 'web', 'src');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
const config = {
  watchFolders: [sharedApiClientDir],
};

module.exports = mergeConfig(getDefaultConfig(projectRoot), config);
