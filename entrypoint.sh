if [[ "${MODE}" == "worker" ]]; then
  exec uv run worker.py
else
  exec uv run app.py
fi


