module.exports = {
  preset: '@react-native/jest-preset',
  // Official mock recommended by @react-native-async-storage/async-storage
  // itself — the real native module doesn't exist in the Jest environment.
  setupFiles: ['./jest.setup.js'],
};
