import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface VideoResponse {
  id: string;
  title: string;
  description: string | null;
  tags: string[] | null;
  video_path: string;
  thumb_path: string | null;
  source_url: string;
  platform: string;
  duration: number | null;
  file_size: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  stream_url: string | null;
  download_url: string | null;
  thumb_url: string | null;
}

export interface VideoListResponse {
  items: VideoResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface VideoUpdate {
  title?: string;
  description?: string;
  tags?: string[];
}

export interface ScrapeRequest {
  query: string;
  target_count: number;
}

export interface ScrapeQueueItem {
  id: string;
  query: string;
  target_count: number;
}

export interface ScrapeStatus {
  is_running: boolean;
  query: string | null;
  target_count: number;
  downloaded_count: number;
  failed_count: number;
  progress_percent: number;
  errors: string[];
  queue: ScrapeQueueItem[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly API = '/api';

  constructor(private http: HttpClient) {}

  // ── Videos ────────────────────────────────────────────────────

  getVideos(page = 1, pageSize = 24, search?: string): Observable<VideoListResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());

    if (search) {
      params = params.set('search', search);
    }

    return this.http.get<VideoListResponse>(`${this.API}/videos`, { params });
  }

  getVideo(id: string): Observable<VideoResponse> {
    return this.http.get<VideoResponse>(`${this.API}/videos/${id}`);
  }

  getNextVideo(id: string): Observable<VideoResponse> {
    return this.http.get<VideoResponse>(`${this.API}/videos/${id}/next`);
  }

  updateVideo(id: string, data: VideoUpdate): Observable<VideoResponse> {
    return this.http.put<VideoResponse>(`${this.API}/videos/${id}`, data);
  }

  deleteVideo(id: string): Observable<{ message: string; id: string }> {
    return this.http.delete<{ message: string; id: string }>(
      `${this.API}/videos/${id}`
    );
  }

  // ── URL Helpers ───────────────────────────────────────────────

  getStreamUrl(id: string): string {
    return `${this.API}/videos/${id}/stream`;
  }

  getDownloadUrl(id: string): string {
    return `${this.API}/videos/${id}/download`;
  }

  getThumbUrl(id: string): string {
    return `${this.API}/videos/${id}/thumb`;
  }

  // ── Scraper ───────────────────────────────────────────────────

  startScrape(request: ScrapeRequest): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.API}/scraper/start`,
      request
    );
  }

  getScrapeStatus(): Observable<ScrapeStatus> {
    return this.http.get<ScrapeStatus>(`${this.API}/scraper/status`);
  }

  stopScrape(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.API}/scraper/stop`, {});
  }

  removeFromQueue(jobId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.API}/scraper/queue/${jobId}`);
  }
}
