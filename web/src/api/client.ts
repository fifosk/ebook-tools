/**
 * API Client - Backward Compatibility Layer
 *
 * This file re-exports all API functions from the new modular structure
 * at `./client/index.ts` for backward compatibility with existing imports.
 *
 * For new code, prefer importing from specific modules:
 * - `./client/base` - Core utilities (apiFetch, auth state)
 * - `./client/auth` - Authentication endpoints
 * - `./client/jobs` - Pipeline and job management
 * - `./client/admin` - User management
 * - `./client/media` - Media, images, video, audio
 * - `./client/library` - Library management
 * - `./client/subtitles` - Subtitle and YouTube endpoints
 */

export * from './client/index';
