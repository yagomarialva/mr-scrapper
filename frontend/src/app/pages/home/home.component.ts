import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, VideoResponse, ScrapeStatus } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { VideoCardComponent } from '../../shared/components/video-card/video-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, VideoCardComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit {
  videos = signal<VideoResponse[]>([]);
  loading = signal(true);
  totalVideos = signal(0);
  currentPage = signal(1);
  pageSize = 24;

  // Search
  searchQuery = signal('');

  // Scraper
  scrapeQuery = '';
  scrapeCount = 10;
  scrapeLoading = signal(false);
  scrapeStatus = signal<ScrapeStatus | null>(null);
  scrapeMessage = signal<string | null>(null);

  private statusInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private api: ApiService,
    private authService: AuthService,
    private router: Router
  ) {}

  get userName(): string {
    return this.authService.currentUser()?.name || 'Usuário';
  }

  get totalPages(): number {
    return Math.ceil(this.totalVideos() / this.pageSize);
  }

  ngOnInit(): void {
    this.loadVideos();
    this.pollScrapeStatus();
  }

  loadVideos(page = 1): void {
    this.loading.set(true);
    this.api.getVideos(page, this.pageSize, this.searchQuery() || undefined).subscribe({
      next: (res) => {
        this.videos.set(res.items);
        this.totalVideos.set(res.total);
        this.currentPage.set(res.page);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  onSearch(query: string): void {
    this.searchQuery.set(query);
    this.loadVideos(1);
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages) {
      this.loadVideos(this.currentPage() + 1);
    }
  }

  prevPage(): void {
    if (this.currentPage() > 1) {
      this.loadVideos(this.currentPage() - 1);
    }
  }

  // ── Scraper Controls ──────────────────────────────────────────

  startScrape(): void {
    if (!this.scrapeQuery.trim()) return;

    this.scrapeLoading.set(true);
    this.scrapeMessage.set(null);

    this.api
      .startScrape({ query: this.scrapeQuery, target_count: this.scrapeCount })
      .subscribe({
        next: (res) => {
          this.scrapeLoading.set(false);
          this.scrapeMessage.set(res.message);
          this.scrapeQuery = ''; // Clear input for next job
          this.pollScrapeStatus();
        },
        error: (err) => {
          this.scrapeLoading.set(false);
          this.scrapeMessage.set(err.error?.detail || 'Erro ao iniciar scraping.');
        },
      });
  }

  removeFromQueue(jobId: string): void {
    this.api.removeFromQueue(jobId).subscribe({
      next: (res) => {
        this.scrapeMessage.set(res.message);
        // Instant visual update before next poll
        const current = this.scrapeStatus();
        if (current) {
          current.queue = current.queue.filter(q => q.id !== jobId);
          this.scrapeStatus.set({...current});
        }
      }
    });
  }

  stopScrape(): void {
    this.api.stopScrape().subscribe({
      next: (res) => {
        this.scrapeMessage.set(res.message);
        this.loadVideos();
      },
    });
  }

  private pollScrapeStatus(): void {
    if (this.statusInterval) clearInterval(this.statusInterval);

    this.statusInterval = setInterval(() => {
      this.api.getScrapeStatus().subscribe({
        next: (status) => {
          this.scrapeStatus.set(status);
          if (!status.is_running && this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
            this.loadVideos();
          }
        },
      });
    }, 3000);
  }

  logout(): void {
    this.authService.logout();
  }

  trackByVideoId(_index: number, video: VideoResponse): string {
    return video.id;
  }
}
