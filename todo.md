# TODO

## Must:

- [ ] Documentation for {path}
- [ ] Filter: OlderThan(years=0, months=0, days=0, hours=0, minutes=0, seconds=0)
- [ ] Filter: NewerThan(years=0, months=0, days=0, hours=0, minutes=0, seconds=0)
- [ ] Filter: FileName(startswith='', endswith='', extension='')
- [ ] Action: Copy(dest)
- [ ] Action: Rename(dest)
- [ ] Documentation for Rename
- [ ] Logfile

## Nice to have:

- [ ] Action: E-Mail
- [ ] Filter: IncompleteDownloads
- [ ] rules.exlude_dotfiles
- [ ] rules.exclude_system_files
- [ ] Warning if multiple rules apply to the same file?
- [ ] Filter: FileSize(bigger_than='2 MB', smaller_than='')
- [ ] Filter: FileType(type='media')
- [ ] Filter modes all, none, any
- [ ] jsonschema for user config validation
- [ ] Action: Zip
- [ ] Action: Notify
- [ ] Undo
- [ ] Tests
- [ ] Filter: Exif
- [ ] Recurse through subfolders?
- [ ] User plugins
- [ ] Action: Print
- [ ] Rule names

## Done:

- [x] Allow no filters -> empty filter list @2017-11-01
- [x] Flatten Filter Extension input @2017-11-01
- [x] Action: Python inline code @2017-10-22
- [x] Regex parse result namespace @2017-10-22
- [x] Formatted output @2017-10-15
- [x] Filter pipelines @2017-10-08
- [x] Accept single folders in config @2017-10-07
- [x] Accept lists and single strings as input for filters and actions @2017-10-07
- [x] Action: Trash @2017-10-05
- [x] Filter: FileExtension(ext) @2017-10-05
- [x] Filter: Regex with named groups @2017-10-05
- [x] Flatten folder list @2017-10-05
- [x] Action: Echo @2017-09-29
- [x] Action pipelines @2017-09-28
- [x] User config file @2017-09-28
- [x] Filter and action listing @2017-09-28
- [x] `setup.py` file
- [x] Action: Shell(cmd)
- [x] Filter: PaperVdi
- [x] Filter: Invoice1and1
- [x] Filter: Regex
- [x] Action: Move
