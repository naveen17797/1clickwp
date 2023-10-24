import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {FormBuilder, FormGroup, Validators} from "@angular/forms";

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.less']
})
export class AppComponent {
  loading = true;
  wpVersion = '';
  multisite = false;
  sites: any[] = [];



  siteForm: FormGroup;


  constructor(private http: HttpClient, private fb: FormBuilder) {
    this.siteForm = this.fb.group({
      version: ['', Validators.required],
      multi_site: [false]
    });
  }

  ngOnInit() {
    this.checkImage();
    this.listSites();
  }

  checkImage() {
    this.http.get('/images/mysql:5.7').subscribe(
      () => {
        this.loading = false;
      },
      () => {
        this.pullImage();
      }
    );
  }

  pullImage() {
    this.http.post('/images/mysql:5.7/pulls', {}).subscribe(
      () => {
        this.checkImage();
      },
      () => {
        console.error('Error pulling image');
      }
    );
  }

  createSite() {
    const body = this.siteForm.value

    this.http.post('/sites', body).subscribe(
      () => {
        alert('Site created successfully!');
        this.listSites();
      },
      () => {
        console.error('Error creating site');
      }
    );
  }

  listSites() {
    this.http.get<any[]>('/sites').subscribe(
      sites => {
        this.sites = sites;
      },
      () => {
        console.error('Error fetching sites');
      }
    );
  }

  deleteSite(siteId: string) {
    this.http.delete(`/sites/${siteId}`).subscribe(
      () => {
        alert('Site deleted successfully!');
        this.listSites();
      },
      () => {
        console.error('Error deleting site');
      }
    );
  }
}
