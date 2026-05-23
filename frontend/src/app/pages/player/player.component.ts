import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService, VideoResponse, VideoUpdate } from '../../core/services/api.service';

@Component({
  selector: 'app-player',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './player.component.html',
  styleUrl: './player.component.css',
})
export class PlayerComponent implements OnInit {
  video = signal<VideoResponse | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  // Edit form
  editTitle = '';
  editDescription = '';
  editTags = '';
  isEditing = signal(false);
  saveLoading = signal(false);
  saveSuccess = signal(false);

  // Delete confirmation
  showDeleteModal = signal(false);
  deleteLoading = signal(false);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (!id) {
        this.error.set('ID do vídeo não encontrado.');
        this.loading.set(false);
        return;
      }

      this.loading.set(true);
      this.api.getVideo(id).subscribe({
        next: (video) => {
          this.video.set(video);
          this.editTitle = video.title;
          this.editDescription = video.description || '';
          this.editTags = (video.tags || []).join(', ');
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Vídeo não encontrado.');
          this.loading.set(false);
        },
      });
    });
  }

  get posterUrl(): string {
    const v = this.video();
    return v && v.thumb_path ? this.api.getThumbUrl(v.id) : '';
  }

  get streamUrl(): string {
    const v = this.video();
    return v ? this.api.getStreamUrl(v.id) : '';
  }

  onVideoEnded(): void {
    const v = this.video();
    if (!v) return;

    this.api.getNextVideo(v.id).subscribe({
      next: (nextVideo) => {
        if (nextVideo && nextVideo.id) {
          this.router.navigate(['/player', nextVideo.id]);
        }
      },
      error: () => {
        console.log('Não há próximo vídeo ou ocorreu um erro.');
      }
    });
  }

  get downloadUrl(): string {
    const v = this.video();
    return v ? this.api.getDownloadUrl(v.id) : '';
  }

  get formattedDuration(): string {
    const d = this.video()?.duration;
    if (!d) return '—';
    const mins = Math.floor(d / 60);
    const secs = Math.floor(d % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  get formattedFileSize(): string {
    const size = this.video()?.file_size;
    if (!size) return '—';
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  get formattedDate(): string {
    const d = this.video()?.created_at;
    if (!d) return '—';
    return new Date(d).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  // ── Edit ──────────────────────────────────────────────────────

  toggleEdit(): void {
    this.isEditing.update((v) => !v);
    this.saveSuccess.set(false);
  }

  saveChanges(): void {
    const v = this.video();
    if (!v) return;

    this.saveLoading.set(true);
    this.saveSuccess.set(false);

    const update: VideoUpdate = {
      title: this.editTitle,
      description: this.editDescription,
      tags: this.editTags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0),
    };

    this.api.updateVideo(v.id, update).subscribe({
      next: (updated) => {
        this.video.set(updated);
        this.saveLoading.set(false);
        this.saveSuccess.set(true);
        this.isEditing.set(false);
      },
      error: () => {
        this.saveLoading.set(false);
        this.error.set('Erro ao salvar alterações.');
      },
    });
  }

  // ── Delete ────────────────────────────────────────────────────

  confirmDelete(): void {
    this.showDeleteModal.set(true);
  }

  cancelDelete(): void {
    this.showDeleteModal.set(false);
  }

  executeDelete(): void {
    const v = this.video();
    if (!v) return;

    this.deleteLoading.set(true);

    this.api.deleteVideo(v.id).subscribe({
      next: () => {
        this.router.navigate(['/']);
      },
      error: () => {
        this.deleteLoading.set(false);
        this.showDeleteModal.set(false);
        this.error.set('Erro ao excluir vídeo.');
      },
    });
  }
}
