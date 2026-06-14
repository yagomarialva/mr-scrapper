import { Injectable, signal } from '@angular/core';
import { Subject } from 'rxjs';

export interface ModalConfig {
  type: 'alert' | 'confirm' | 'prompt';
  title: string;
  message: string;
  placeholder?: string; // For prompt
  confirmText?: string;
  cancelText?: string;
}

@Injectable({ providedIn: 'root' })
export class ModalService {
  modalConfig = signal<ModalConfig | null>(null);
  
  private responseSubject = new Subject<any>();

  alert(title: string, message: string, confirmText = 'OK'): Promise<void> {
    this.modalConfig.set({ type: 'alert', title, message, confirmText });
    return new Promise(resolve => {
      this.responseSubject.subscribe(() => {
        this.close();
        resolve();
      });
    });
  }

  confirm(title: string, message: string, confirmText = 'Confirmar', cancelText = 'Cancelar'): Promise<boolean> {
    this.modalConfig.set({ type: 'confirm', title, message, confirmText, cancelText });
    return new Promise(resolve => {
      this.responseSubject.subscribe((res: boolean) => {
        this.close();
        resolve(res);
      });
    });
  }

  prompt(title: string, message: string, placeholder = '', confirmText = 'OK', cancelText = 'Cancelar'): Promise<string | null> {
    this.modalConfig.set({ type: 'prompt', title, message, placeholder, confirmText, cancelText });
    return new Promise(resolve => {
      this.responseSubject.subscribe((res: string | null) => {
        this.close();
        resolve(res);
      });
    });
  }

  submit(result: any) {
    this.responseSubject.next(result);
  }

  close() {
    this.modalConfig.set(null);
    this.responseSubject = new Subject<any>(); // Reset for next call
  }
}
