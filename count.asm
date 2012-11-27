            SET I, 0
    :loop   IFE I, 10
              SET PC, crash
            ADD I, 1
            SET PC, loop
    :crash  SET A, 1        
            SET PC, crash
