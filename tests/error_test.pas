! ============================================================
! Error Test Program – demonstrates error recovery
! This file contains deliberate errors
! ============================================================
program ErrorTest;

var
    x, y : integer;
    z    : integer;

begin
    x := 10;
    y := 20 +;          ! PARSE ERROR: missing operand after +
    z := undeclared;    ! SEM ERROR: undeclared variable
    write(x + y);
    if x > 0 then
        write('positive')
    else
        write('non-positive');
    while x > 0 do
    begin
        x := x - 1
    end
end.
