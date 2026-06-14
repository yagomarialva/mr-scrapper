import { Component, ElementRef, ViewChild, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModalService } from '../../../core/services/modal.service';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './modal.component.html',
  styleUrl: './modal.component.css'
})
export class ModalComponent {
  @ViewChild('dialog') dialogRef!: ElementRef<HTMLDialogElement>;
  
  promptValue = '';

  constructor(public modalService: ModalService) {
    effect(() => {
      const config = this.modalService.modalConfig();
      if (config && this.dialogRef?.nativeElement) {
        this.promptValue = ''; // Reset prompt
        this.dialogRef.nativeElement.showModal();
      } else if (!config && this.dialogRef?.nativeElement) {
        this.dialogRef.nativeElement.close();
      }
    });
  }

  onConfirm() {
    const config = this.modalService.modalConfig();
    if (config?.type === 'prompt') {
      this.modalService.submit(this.promptValue);
    } else if (config?.type === 'confirm') {
      this.modalService.submit(true);
    } else {
      this.modalService.submit(null); // Alert
    }
  }

  onCancel() {
    const config = this.modalService.modalConfig();
    if (config?.type === 'prompt') {
      this.modalService.submit(null);
    } else if (config?.type === 'confirm') {
      this.modalService.submit(false);
    }
  }
}
