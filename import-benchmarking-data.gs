// Much of this code is from this blog post:
// https://spreadsheet.dev/how-to-import-csv-files-into-google-sheets-using-apps-script

gBenchmarkingFolderName = "DMFsim-python-raw-data";
gRounds = 3;    // number csv data per row

function importMachineData(machineName, machineCSVFiles)
{
  // consistent ordering of files
  machineCSVFiles.sort();

  // make new spread sheet
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.insertSheet(machineName);

  // import data to that sheet one by one in r-c order
  var row = 1;
  var col = 1;
  var maxDataPointsInRow = -1;
  for (var i = 0; i < machineCSVFiles.length; i++)
  {
    var csvData = Utilities.parseCsv(machineCSVFiles[i].getBlob().getDataAsString());
    // header
    sheet.getRange(row, col, 1, 1).setValue(machineCSVFiles[i].getName());
    // csv contents
    sheet.getRange(row + 1, col, csvData.length, csvData[0].length).setValues(csvData);

    // update max cols in row
    maxDataPointsInRow = Math.max(maxDataPointsInRow, csvData.length);

    // update index
    if ((i + 1) % gRounds !== 0)     // if we just set values for the last csv file in the row
    {
      col += csvData[0].length + 1;
    }
    else
    {
      col = 1;
      row += maxDataPointsInRow + 2;
      maxDataPointsInRow = -1;
    }
  }
}

// Returns folders in Google Drive that have a certain name.
function findFoldersInDrive(folderName)
{
  var folders = DriveApp.getFoldersByName(folderName);
  var result = [];
  while(folders.hasNext())
    result.push(folders.next());
  return result;
}

// Returns files from a Google Drive folder.
function getFilesFromFolder(folder)
{
  var files = folder.getFiles();
  var result = [];
  while(files.hasNext())
    result.push(files.next());
  return result;
}

// main function
function main()
{
  // locate folder in drive with data
  var folders = findFoldersInDrive(gBenchmarkingFolderName);
  if (folders.length === 1)
  {
    var rootFolder = folders[0];
    var machineFolders = rootFolder.getFolders();
    while (machineFolders.hasNext())
    {
      var machineFolder = machineFolders.next();
      var machineName = machineFolder.getName();
      importMachineData(machineName, getFilesFromFolder(machineFolder));
    }
  }
}