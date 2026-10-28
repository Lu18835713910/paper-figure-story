param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference='Stop'
function FileSha([string]$Path){
 $stream=[IO.File]::OpenRead($Path);$algorithm=[Security.Cryptography.SHA256]::Create()
 try {return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
 finally {$stream.Dispose();$algorithm.Dispose()}
}
$spec=Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$source=[IO.Path]::GetFullPath($spec.input)
$before=FileSha $source
if($spec.input_sha256 -and $before -ne $spec.input_sha256){throw 'RENDER_INPUT_DRIFT'}
$out=[IO.Path]::GetFullPath($spec.outdir)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$app=New-Object -ComObject PowerPoint.Application
$initialCount=$app.Presentations.Count
$presentation=$null;$owned=$false;$records=@()
try {
 foreach($candidate in $app.Presentations){if($candidate.FullName -eq $source){$presentation=$candidate;break}}
 if($null -eq $presentation){$presentation=$app.Presentations.Open($source,-1,0,0);$owned=$true}
 $wanted=@()
 if($null -ne $spec.slides){$wanted=@($spec.slides)}
 foreach($slide in $presentation.Slides){
  if($wanted.Count -gt 0 -and $wanted -notcontains $slide.SlideIndex){continue}
  $issues=@();$objects=@();$tables=@()
  foreach($shape in $slide.Shapes){
   $off=$shape.Left -lt -1 -or $shape.Top -lt -1 -or ($shape.Left+$shape.Width) -gt ($presentation.PageSetup.SlideWidth+1) -or ($shape.Top+$shape.Height) -gt ($presentation.PageSetup.SlideHeight+1)
   if($off){$issues+=@{code='OFF_CANVAS';shape=$shape.Name;id=$shape.Id}}
   if($shape.HasTextFrame -and $shape.TextFrame.HasText){
    $frame=$shape.TextFrame2;$available=$shape.Height-$frame.MarginTop-$frame.MarginBottom
    $overflow=$frame.TextRange.BoundHeight -gt ($available+3)
    if($overflow){$issues+=@{code='TEXT_HEIGHT_OVERFLOW';shape=$shape.Name;id=$shape.Id;actual=$frame.TextRange.BoundHeight;available=$available}}
    $objects+=@{id=$shape.Id;name=$shape.Name;text=$shape.TextFrame.TextRange.Text;bounds=@($shape.Left,$shape.Top,$shape.Width,$shape.Height);text_bounds=@($frame.TextRange.BoundLeft,$frame.TextRange.BoundTop,$frame.TextRange.BoundWidth,$frame.TextRange.BoundHeight);text_height=$frame.TextRange.BoundHeight;available_height=$available;overflow=$overflow}
   }
   if($shape.HasTable){
    for($row=1;$row -le $shape.Table.Rows.Count;$row++){
     for($col=1;$col -le $shape.Table.Columns.Count;$col++){
      $cell=$shape.Table.Cell($row,$col).Shape;$tf=$cell.TextFrame2;$available=$cell.Height-$tf.MarginTop-$tf.MarginBottom
      $overflow=$tf.TextRange.BoundHeight -gt ($available+3)
      if($overflow){$issues+=@{code='TABLE_CELL_OVERFLOW';shape=$shape.Name;id=$shape.Id;row=$row;column=$col;actual=$tf.TextRange.BoundHeight;available=$available}}
      $tables+=@{shape=$shape.Name;row=$row;column=$col;text=$cell.TextFrame.TextRange.Text;overflow=$overflow}
     }
    }
   }
  }
  $width=if($spec.width){[int]$spec.width}else{1920}
  $height=[math]::Round($width*$presentation.PageSetup.SlideHeight/$presentation.PageSetup.SlideWidth)
  $png=Join-Path $out ('slide-{0:d3}.png' -f $slide.SlideIndex)
  $slide.Export($png,'PNG',$width,$height)
  $records+=@{slide=$slide.SlideIndex;png=$png;png_sha256=(FileSha $png);width=$width;height=$height;issues=$issues;text_objects=$objects;table_cells=$tables}
 }
 $receipt=@{input=$source;input_sha256=$before;engine='Microsoft PowerPoint';version=$app.Version;slides=$presentation.Slides.Count;width_pt=$presentation.PageSetup.SlideWidth;height_pt=$presentation.PageSetup.SlideHeight;rendered=$records;source_unchanged=($before -eq (FileSha $source));visual_acceptance='PENDING'}
} finally {
 if($owned -and $null -ne $presentation){$presentation.Close()}
 if($initialCount -eq 0){$app.Quit()}
}
$receipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $spec.receipt -Encoding UTF8
Write-Output ('PowerPoint export: '+$records.Count+' slide(s)')
