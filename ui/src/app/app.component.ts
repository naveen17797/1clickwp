import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {FormArray, FormBuilder, FormControl, FormGroup, Validators} from "@angular/forms";
import {environment} from "../environments/environment";

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.less']
})
export class AppComponent {
  loading = true;

  multisite = false;
  sites: any[] = [];
  siteForm: FormGroup;


  constructor(private http: HttpClient, private fb: FormBuilder) {
    let existing = []
    try {
      // @ts-ignore
      existing = JSON.parse(localStorage.getItem('volume_bindings'))
      existing = existing.map((e: { host_path: any; container_path: any; }) => this.fb.group({
        host_path: [e.host_path, Validators.required],
        container_path: [e.container_path, Validators.required]
      }))
    }
    catch (e) {
      existing = []
    }


    this.siteForm = this.fb.group({
      version: ['6.0.0', Validators.required],
      multi_site: [false],
      // @ts-ignore
      volume_bindings: this.fb.array(existing),
      cpu: [''],
      memory: [''],
      wp_debug: [true]
    });
  }

  // Getter for easier access to the volume_bindings form array
  get volumeBindings(): FormArray<FormGroup> {
    return this.siteForm.get('volume_bindings') as FormArray;
  }

  // Function to add a new row to the form array
  addVolumeBindingRow() {
    const newRow = this.fb.group({
      host_path: ['', Validators.required],
      container_path: ['', Validators.required]
    });

    this.volumeBindings.push(newRow);
  }

  // Function to remove a row from the form array
  removeVolumeBindingRow(index: number) {
    this.volumeBindings.removeAt(index);
  }

  ngOnInit() {
    this.checkImage();
    this.listSites();
  }

  checkImage() {
    this.http.get(environment.baseUrl + '/images/mysql:5.7').subscribe(
      () => {
        this.loading = false;
      },
      () => {
        this.pullImage();
      }
    );
  }

  pullImage() {
    this.http.post(environment.baseUrl + '/images/mysql:5.7/pulls', {}).subscribe(
      () => {
        this.checkImage();
      },
      () => {
        console.error('Error pulling image');
      }
    );
  }

  createSite() {
    this.loading = true
    const body = this.siteForm.value

    localStorage.setItem('volume_bindings', JSON.stringify(body.volume_bindings))

    this.http.post(environment.baseUrl + '/sites', body).subscribe(
      () => {
        this.loading = false
        this.listSites();
      },
      () => {
        console.error('Error creating site');
      }
    );
  }

  listSites() {
    this.loading = true
    this.http.get<any[]>(environment.baseUrl + '/sites').subscribe(
      sites => {
        this.sites = sites;
      },
      () => {
        console.error('Error fetching sites');
      }, () => {
        this.loading = false
      }
    );
  }

  deleteSite(siteId: string) {
    this.loading = true
    this.http.delete(environment.baseUrl + `/sites/${siteId}`).subscribe(
      () => {
        this.loading = false
        this.listSites();
      },
      () => {
        console.error('Error deleting site');
      }
    );
  }
}
