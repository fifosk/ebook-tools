import { describe, expect, it } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider
} from '../../api/dtos';
import {
  bookDiscoveryProviderUnavailableMessage,
  buildBookNarrationDiscoveryProviderOptions,
  DEFAULT_BOOK_DISCOVERY_PROVIDER,
  filterBookNarrationDiscoveryCandidates,
  isBookDiscoveryProvider,
  resolveDefaultBookDiscoveryProvider
} from '../book-narration/bookNarrationDiscoveryProviders';

function provider(overrides: Partial<AcquisitionProvider>): AcquisitionProvider {
  const mediaKinds = overrides.media_kinds ?? ['book'];
  const discoveryMediaKinds = overrides.discovery_media_kinds ?? mediaKinds;
  return {
    id: 'local_epub',
    label: 'Local EPUB library',
    media_kinds: mediaKinds,
    capabilities: ['import_local'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['user_provided'],
    discovery_media_kinds: discoveryMediaKinds,
    default_eligible_media_kinds: overrides.default_eligible_media_kinds ?? discoveryMediaKinds,
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

function candidate(overrides: Partial<AcquisitionCandidate>): AcquisitionCandidate {
  return {
    candidate_id: 'local-1',
    provider: 'local_epub',
    media_kind: 'book',
    title: 'Local Book',
    rights: 'user_provided',
    capabilities: ['import_local'],
    candidate_token: 'token',
    contributors: [],
    local_path: '/books/local.epub',
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function discoveryResponse(
  candidates: AcquisitionCandidate[],
  providersQueried: string[] = []
): AcquisitionDiscoveryResponse {
  return {
    candidates,
    providers_queried: providersQueried,
    policy_notes: []
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
      {
        id: 'zlibrary_attended',
        label: 'Z-Library import',
        unavailableMessage: 'Direct Z-Library automation is intentionally disabled. Use attended browser downloads, then import the EPUB through Manual downloads or Choose EPUB.'
      }
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

  it('keeps attended-only Z-Library imports out of Web discovery and default fanout', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'], default_eligible_media_kinds: ['book'] }),
      provider({
        id: 'zlibrary_attended',
        label: 'Z-Library attended import',
        capabilities: ['import_local'],
        status: 'planned',
        configured: false,
        available: false,
        rights: ['unknown', 'restricted'],
        discovery_media_kinds: [],
        default_eligible_media_kinds: [],
        policy_notes: ['Direct Z-Library automation is intentionally disabled.']
      })
    ];

    expect(buildBookNarrationDiscoveryProviderOptions(providers)).toEqual([
      { id: 'local_epub', label: 'Local EPUBs', unavailableMessage: null }
    ]);
    expect(isBookDiscoveryProvider(providers[1])).toBe(false);
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['zlibrary_attended', 'local_epub'] },
      providers,
      fallback: 'local_epub'
    })).toBe('local_epub');
  });

  it('uses backend default sources when multiple book defaults are available', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'] }),
      provider({ id: 'manual_downloads', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'internet_archive', capabilities: ['search', 'metadata', 'acquire'] })
    ];

    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['internet_archive', 'local_epub'] },
      providers,
      fallback: 'local_epub'
    })).toBe(DEFAULT_BOOK_DISCOVERY_PROVIDER);
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['missing_provider'] },
      providers,
      fallback: 'local_epub'
    })).toBe('local_epub');
  });

  it('uses a concrete backend default when only one book default is available', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'] }),
      provider({ id: 'internet_archive', capabilities: ['search', 'metadata', 'acquire'] })
    ];

    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['internet_archive'] },
      providers,
      fallback: 'local_epub'
    })).toBe('internet_archive');
  });

  it('adds a backend default sources option when multiple book defaults are available', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'] }),
      provider({ id: 'manual_downloads', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'internet_archive', capabilities: ['search', 'metadata', 'acquire'] })
    ];

    expect(buildBookNarrationDiscoveryProviderOptions(providers, {
      book: ['local_epub', 'manual_downloads']
    })).toEqual([
      { id: DEFAULT_BOOK_DISCOVERY_PROVIDER, label: 'Default sources', unavailableMessage: null },
      { id: 'local_epub', label: 'Local EPUBs', unavailableMessage: null },
      { id: 'manual_downloads', label: 'Manual downloads', unavailableMessage: null },
      { id: 'internet_archive', label: 'Internet Archive', unavailableMessage: null }
    ]);
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['local_epub', 'manual_downloads'] },
      providers,
      fallback: 'local_epub'
    })).toBe(DEFAULT_BOOK_DISCOVERY_PROVIDER);
  });

  it('uses backend default eligibility when deciding book default sources', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'], default_eligible_media_kinds: ['book'] }),
      provider({
        id: 'internet_archive',
        capabilities: ['search', 'metadata', 'acquire'],
        default_eligible_media_kinds: []
      }),
      provider({ id: 'manual_downloads', media_kinds: ['book', 'video'], default_eligible_media_kinds: ['book'] })
    ];

    expect(buildBookNarrationDiscoveryProviderOptions(providers, {
      book: ['local_epub', 'internet_archive']
    })).toEqual([
      { id: 'local_epub', label: 'Local EPUBs', unavailableMessage: null },
      { id: 'manual_downloads', label: 'Manual downloads', unavailableMessage: null },
      { id: 'internet_archive', label: 'Internet Archive', unavailableMessage: null }
    ]);
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['internet_archive', 'local_epub'] },
      providers,
      fallback: 'local_epub'
    })).toBe('local_epub');
  });

  it('treats missing backend book default eligibility as non-defaultable after inventory loads', () => {
    const providers = [
      provider({
        id: 'partner_catalog',
        label: 'Partner Catalog',
        capabilities: ['search', 'metadata'],
        discovery_media_kinds: ['book'],
        default_eligible_media_kinds: undefined as unknown as AcquisitionProvider['default_eligible_media_kinds']
      }),
      provider({ id: 'local_epub', capabilities: ['import_local'], default_eligible_media_kinds: ['book'] })
    ];

    expect(buildBookNarrationDiscoveryProviderOptions(providers, {
      book: ['partner_catalog', 'local_epub']
    }).map((entry) => entry.id)).toEqual(['local_epub', 'partner_catalog']);
    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['partner_catalog', 'local_epub'] },
      providers,
      fallback: 'local_epub'
    })).toBe('local_epub');
  });

  it('uses default sources when multiple non-disabled book defaults remain available', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'], status: 'not_configured', available: false }),
      provider({ id: 'manual_downloads', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'internet_archive', capabilities: ['search', 'metadata', 'acquire'] })
    ];

    expect(resolveDefaultBookDiscoveryProvider({
      defaultProviderIds: { book: ['local_epub', 'manual_downloads', 'internet_archive'] },
      providers,
      fallback: 'local_epub'
    })).toBe(DEFAULT_BOOK_DISCOVERY_PROVIDER);
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

  it('filters default source candidates to backend-queried default-eligible book providers', () => {
    const providers = [
      provider({ id: 'local_epub', capabilities: ['import_local'], default_eligible_media_kinds: ['book'] }),
      provider({
        id: 'internet_archive',
        capabilities: ['search', 'metadata', 'acquire'],
        default_eligible_media_kinds: []
      }),
      provider({
        id: 'manual_downloads',
        media_kinds: ['book', 'video'],
        capabilities: ['import_local'],
        default_eligible_media_kinds: ['book']
      })
    ];

    expect(filterBookNarrationDiscoveryCandidates(
      discoveryResponse([
        candidate({ candidate_id: 'local', provider: 'local_epub' }),
        candidate({ candidate_id: 'manual', provider: 'manual_downloads', local_path: '/manual/book.epub' }),
        candidate({ candidate_id: 'archive', provider: 'internet_archive', capabilities: ['acquire'], local_path: null }),
        candidate({ candidate_id: 'missing', provider: 'partner_catalog', capabilities: ['metadata'], local_path: null }),
        candidate({ candidate_id: 'video', provider: 'manual_downloads', media_kind: 'video' })
      ], ['local_epub', 'manual_downloads', 'partner_catalog']),
      DEFAULT_BOOK_DISCOVERY_PROVIDER,
      providers
    ).map((entry) => entry.candidate_id)).toEqual(['local', 'manual']);
  });

  it('filters concrete provider searches to selectable candidates from that provider', () => {
    expect(filterBookNarrationDiscoveryCandidates(
      discoveryResponse([
        candidate({ candidate_id: 'local', provider: 'local_epub' }),
        candidate({ candidate_id: 'manual', provider: 'manual_downloads', local_path: '/manual/book.epub' }),
        candidate({ candidate_id: 'disabled', provider: 'manual_downloads', local_path: null, capabilities: [] })
      ], ['manual_downloads']),
      'manual_downloads'
    ).map((entry) => entry.candidate_id)).toEqual(['manual']);
  });

  it('uses backend source labels for unavailable source-backed providers', () => {
    const providers = [
      provider({
        id: 'local_epub',
        label: 'Local EPUB library',
        status: 'not_configured',
        configured: true,
        available: false,
        source_label: 'Books root'
      })
    ];

    expect(bookDiscoveryProviderUnavailableMessage('local_epub', providers)).toBe(
      'Local EPUB library is not configured. Configure books root or choose another discovery source.'
    );
  });
});
