import { describe, expect, it } from 'vitest';
import type { AcquisitionProvider } from '../../api/dtos';
import {
  bookDiscoveryProviderUnavailableMessage,
  buildBookNarrationDiscoveryProviderOptions,
  isBookDiscoveryProvider,
  resolveDefaultBookDiscoveryProvider
} from '../book-narration/bookNarrationDiscoveryProviders';

function provider(overrides: Partial<AcquisitionProvider>): AcquisitionProvider {
  return {
    id: 'local_epub',
    label: 'Local EPUB library',
    media_kinds: ['book'],
    capabilities: ['import_local'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['user_provided'],
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

describe('bookNarrationDiscoveryProviders', () => {
  it('returns familiar fallback provider options before the backend registry loads', () => {
    expect(buildBookNarrationDiscoveryProviderOptions([])).toEqual([
      { id: 'local_epub', label: 'Local EPUBs', unavailableMessage: null },
      { id: 'manual_downloads', label: 'Manual downloads', unavailableMessage: null },
      { id: 'gutenberg', label: 'Gutenberg', unavailableMessage: null },
      { id: 'internet_archive', label: 'Internet Archive', unavailableMessage: null },
      { id: 'openlibrary', label: 'Open Library', unavailableMessage: null },
      { id: 'zlibrary_attended', label: 'Z-Library import', unavailableMessage: null }
    ]);
  });

  it('keeps backend book providers in stable UI order and preserves backend labels for unknown catalogs', () => {
    const options = buildBookNarrationDiscoveryProviderOptions([
      provider({ id: 'partner_catalog', label: 'Partner Catalog', capabilities: ['search', 'metadata'] }),
      provider({ id: 'manual_downloads', label: 'Manual folder', media_kinds: ['book', 'video'] }),
      provider({ id: 'gutenberg', label: 'Gutendex backend', capabilities: ['search', 'metadata', 'acquire'] }),
      provider({ id: 'video_only', label: 'Video only', media_kinds: ['video'], capabilities: ['search'] })
    ]);

    expect(options).toEqual([
      { id: 'manual_downloads', label: 'Manual downloads', unavailableMessage: null },
      { id: 'gutenberg', label: 'Gutenberg', unavailableMessage: null },
      { id: 'partner_catalog', label: 'Partner Catalog', unavailableMessage: null }
    ]);
  });

  it('prefers backend discovery media kind declarations over capability guesses', () => {
    expect(isBookDiscoveryProvider(provider({
      id: 'metadata_search_without_discovery',
      capabilities: ['search', 'metadata'],
      discovery_media_kinds: []
    }))).toBe(false);
    expect(isBookDiscoveryProvider(provider({
      id: 'book_metadata_catalog',
      media_kinds: ['video'],
      capabilities: ['metadata'],
      discovery_media_kinds: ['book']
    }))).toBe(true);
  });

  it('uses backend default book provider ids before falling back to local_epub', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'] }),
      provider({ id: 'manual_downloads', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'internet_archive', capabilities: ['search', 'metadata', 'acquire'] })
    ];

    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['internet_archive', 'local_epub'] },
      providers,
      fallback: 'local_epub'
    })).toBe('internet_archive');
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['missing_provider'] },
      providers,
      fallback: 'local_epub'
    })).toBe('local_epub');
  });

  it('reports unavailable provider guidance with backend policy notes when present', () => {
    const providers = [
      provider({
        id: 'manual_downloads',
        label: 'Manual download folders',
        media_kinds: ['book', 'video'],
        status: 'not_configured',
        configured: false,
        available: false,
        policy_notes: ['Configure manual download roots first.']
      })
    ];

    expect(bookDiscoveryProviderUnavailableMessage('manual_downloads', providers)).toBe(
      'Manual download folders is not configured. Configure manual download roots first.'
    );
    expect(bookDiscoveryProviderUnavailableMessage('gutenberg', providers)).toBe(
      'Gutenberg is unavailable on this backend. Choose another discovery source.'
    );
  });
});
