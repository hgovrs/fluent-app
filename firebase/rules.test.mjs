import { readFile } from 'node:fs/promises';
import { after, before, beforeEach, test } from 'node:test';
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} from '@firebase/rules-unit-testing';
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  serverTimestamp,
  setDoc,
  Timestamp,
} from 'firebase/firestore';

let environment;
const path = 'users/alice/backups/progress';
const valid = () => ({
  schemaVersion: 1,
  payload: '{"completedLessons":[]}',
  updatedAt: serverTimestamp(),
});
const database = (uid) => uid
  ? environment.authenticatedContext(uid).firestore()
  : environment.unauthenticatedContext().firestore();

before(async () => {
  environment = await initializeTestEnvironment({
    projectId: 'demo-fluent',
    firestore: {
      rules: await readFile(new URL('../firestore.rules', import.meta.url), 'utf8'),
    },
  });
});
beforeEach(async () => environment.clearFirestore());
after(async () => environment?.cleanup());

test('owner can explicitly create, restore, replace and delete backup', async () => {
  const reference = doc(database('alice'), path);
  await assertSucceeds(setDoc(reference, valid()));
  await assertSucceeds(getDoc(reference));
  await assertSucceeds(setDoc(reference, { ...valid(), payload: '{}' }));
  await assertSucceeds(deleteDoc(reference));
});

test('unauthenticated and different users cannot access owner backup', async () => {
  await assertSucceeds(setDoc(doc(database('alice'), path), valid()));
  for (const uid of [undefined, 'bob']) {
    const reference = doc(database(uid), path);
    await assertFails(getDoc(reference));
    await assertFails(setDoc(reference, valid()));
    await assertFails(deleteDoc(reference));
  }
});

test('reject unknown keys, missing keys, wrong types and schema versions', async () => {
  const reference = doc(database('alice'), path);
  for (const change of [
    { extra: true },
    { schemaVersion: 2 },
    { schemaVersion: '1' },
    { schemaVersion: 1.5 },
    { payload: {} },
    { payload: null },
    { updatedAt: 'today' },
    { updatedAt: Timestamp.fromMillis(0) },
  ]) {
    await assertFails(setDoc(reference, { ...valid(), ...change }));
  }
  for (const key of ['schemaVersion', 'payload', 'updatedAt']) {
    const data = valid();
    delete data[key];
    await assertFails(setDoc(reference, data));
  }
});

test('enforce payload size boundary', async () => {
  const reference = doc(database('alice'), path);
  await assertSucceeds(setDoc(reference, {
    ...valid(), payload: 'a'.repeat(199999),
  }));
  await assertFails(setDoc(reference, {
    ...valid(), payload: 'a'.repeat(200000),
  }));
});

test('deny listing and all other document paths', async () => {
  const db = database('alice');
  await assertFails(getDocs(collection(db, 'users/alice/backups')));
  for (const other of [
    'users/alice',
    'users/alice/backups/other',
    'users/alice/backups/progress/nested/document',
    'public/document',
  ]) {
    await assertFails(getDoc(doc(db, other)));
    await assertFails(setDoc(doc(db, other), valid()));
  }
});
