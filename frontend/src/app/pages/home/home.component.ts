import { Component, OnInit, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom, Subject, takeUntil, interval } from 'rxjs';
import { ApiService, VideoResponse, ScrapeStatus } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ModalService } from '../../core/services/modal.service';
import { VideoCardComponent } from '../../shared/components/video-card/video-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, VideoCardComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit, OnDestroy {
  videos = signal<VideoResponse[]>([]);
  loading = signal(true);
  totalVideos = signal(0);
  currentPage = signal(1);
  pageSize = 24;

  // View & Selection
  viewMode = signal<'grid' | 'list'>('grid');
  selectedVideos = signal<Set<string>>(new Set());

  // Search
  searchQuery = signal('');

  // Scraper
  scrapeQuery = '';
  scrapeCount = 10;
  scrapeLoading = signal(false);
  scrapeStatus = signal<ScrapeStatus | null>(null);
  scrapeMessage = signal<string | null>(null);

  private destroy$ = new Subject<void>();
  private statusInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private api: ApiService,
    private authService: AuthService,
    private router: Router,
    private modal: ModalService
  ) {}

  get userName(): string {
    return this.authService.currentUser()?.name || 'Usuário';
  }

  get totalPages(): number {
    return Math.ceil(this.totalVideos() / this.pageSize);
  }

  ngOnInit(): void {
    const savedMode = localStorage.getItem('mrscrap_view_mode');
    if (savedMode === 'grid' || savedMode === 'list') {
      this.viewMode.set(savedMode);
    }
    this.loadVideos();
    this.pollScrapeStatus();
  }

  toggleViewMode(mode: 'grid' | 'list'): void {
    this.viewMode.set(mode);
    localStorage.setItem('mrscrap_view_mode', mode);
  }

  // ── Selection Logic ───────────────────────────────────────────

  toggleSelection(videoId: string, isSelected: boolean): void {
    const current = new Set(this.selectedVideos());
    if (isSelected) {
      current.add(videoId);
    } else {
      current.delete(videoId);
    }
    this.selectedVideos.set(current);
  }

  async selectAll(): Promise<void> {
    this.loading.set(true);
    try {
      const searchParam = this.searchQuery() || undefined;
      const allIds = await firstValueFrom(this.api.getAllVideoIds(searchParam));
      this.selectedVideos.set(new Set(allIds));
    } catch (e) {
      this.modal.alert('Erro', 'Não foi possível selecionar todos os vídeos.');
    } finally {
      this.loading.set(false);
    }
  }

  clearSelection(): void {
    this.selectedVideos.set(new Set());
  }

  // ── Bulk Actions ──────────────────────────────────────────────

  async bulkDelete(): Promise<void> {
    const ids = Array.from(this.selectedVideos());
    if (!ids.length) return;

    const confirmed = await this.modal.confirm(
      'Excluir Vídeos', 
      `Tem certeza que deseja excluir ${ids.length} vídeo(s) da base de dados e do disco?`
    );
    if (!confirmed) return;

    this.loading.set(true);
    this.api.bulkDelete(ids).subscribe({
      next: (res) => {
        this.modal.alert('Sucesso', res.message);
        this.clearSelection();
        this.loadVideos(this.currentPage());
      },
      error: (err) => {
        this.modal.alert('Erro', err.error?.detail || 'Erro ao excluir vídeos.');
        this.loading.set(false);
      }
    });
  }

  bulkDownload(): void {
    const ids = Array.from(this.selectedVideos());
    if (!ids.length) return;

    // Trigger individual downloads in the browser
    ids.forEach((id, index) => {
      setTimeout(() => {
        const url = this.api.getDownloadUrl(id);
        window.open(url, '_blank');
      }, index * 500); // Stagger downloads slightly to prevent browser blocking
    });
    
    this.clearSelection();
  }

  async bulkEdit(): Promise<void> {
    const ids = Array.from(this.selectedVideos());
    if (!ids.length) return;

    const tagsInput = await this.modal.prompt(
      'Editar Tags em Lote', 
      `Digite as novas tags separadas por vírgula para ${ids.length} vídeos (vai sobrescrever as tags atuais):`,
      'Ex: tecnologia, tutorial, ai'
    );
    if (tagsInput === null) return;

    const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
    
    this.loading.set(true);
    this.api.bulkEdit(ids, { tags }).subscribe({
      next: (res) => {
        this.modal.alert('Sucesso', res.message);
        this.clearSelection();
        this.loadVideos(this.currentPage());
      },
      error: (err) => {
        this.modal.alert('Erro', err.error?.detail || 'Erro ao editar vídeos.');
        this.loading.set(false);
      }
    });
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

  ngOnDestroy(): void {
    if (this.statusInterval) clearInterval(this.statusInterval);
    this.destroy$.next();
    this.destroy$.complete();
  }
}
