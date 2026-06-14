import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, VideoResponse } from '../../../core/services/api.service';

@Component({
  selector: 'app-video-card',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './video-card.component.html',
  styleUrl: './video-card.component.css',
})
export class VideoCardComponent {
  @Input({ required: true }) video!: VideoResponse;
  @Input() selectable = false;
  @Input() selected = false;
  @Output() selectionChange = new EventEmitter<boolean>();

  isHovered = false;

  constructor(private api: ApiService) {}

  get thumbSrc(): string {
    return this.video.thumb_path ? this.api.getThumbUrl(this.video.id) : '';
  }

  get videoStreamUrl(): string {
    return this.api.getStreamUrl(this.video.id);
  }

  get formattedDuration(): string {
    if (!this.video.duration) return '';
    const mins = Math.floor(this.video.duration / 60);
    const secs = Math.floor(this.video.duration % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  get formattedDate(): string {
    const d = new Date(this.video.created_at);
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  onThumbError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
  }

  onMouseEnter(): void {
    this.isHovered = true;
  }

  onMouseLeave(): void {
    this.isHovered = false;
  }

  onTimeUpdate(event: Event): void {
    const videoElement = event.target as HTMLVideoElement;
    // Loop the first 7 seconds
    if (videoElement.currentTime >= 7) {
      videoElement.currentTime = 0;
      videoElement.play().catch(() => {});
    }
  }

  toggleSelection(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.selected = !this.selected;
    this.selectionChange.emit(this.selected);
  }
}
